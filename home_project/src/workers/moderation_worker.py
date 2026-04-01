import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from aiokafka import AIOKafkaConsumer
import asyncpg.exceptions as apg_exc

from database import get_db_pool, close_db_pool
from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultsRepository
from services.predictions import PredictionService
from models.predictions import PredictionRequest
from models.moderation import ModerationResultResponse
from storage.prediction_cache import prediction_cache
from clients.kafka import send_to_dlq
from model import get_model

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
MODERATION_TOPIC = "moderation"
MAX_RETRIES = 3
RETRY_DELAY_BASE_SECONDS = float(os.getenv("RETRY_DELAY_BASE_SECONDS", "5"))

item_repository = ItemRepository()
moderation_repository = ModerationResultsRepository()
prediction_service = PredictionService()

_RETRYABLE_ASYNCPG = tuple(
    getattr(apg_exc, name)
    for name in (
        "InterfaceError",
        "InternalClientError",
        "ConnectionDoesNotExistError",
        "CannotConnectNowError",
        "TooManyConnectionsError",
    )
    if hasattr(apg_exc, name)
)


def retry_delay_seconds(retry_count: int) -> float:
    return RETRY_DELAY_BASE_SECONDS * (2 ** retry_count)


async def _cache_moderation_task(
    task_id: int,
    status: str,
    *,
    is_violation: Optional[bool] = None,
    probability: Optional[float] = None,
    error_message: Optional[str] = None,
) -> None:
    await prediction_cache.set_moderation_result(
        task_id,
        ModerationResultResponse(
            task_id=task_id,
            status=status,
            is_violation=is_violation,
            probability=probability,
            error_message=error_message,
        ),
    )


def is_retryable_error(error: Exception) -> bool:
    if isinstance(error, (ConnectionError, OSError, TimeoutError)):
        return True
    if _RETRYABLE_ASYNCPG and isinstance(error, _RETRYABLE_ASYNCPG):
        return True
    if isinstance(error, RuntimeError):
        msg = str(error).lower()
        if "модель не загружена" in msg or "model" in msg:
            return True
    return False


async def _fail_task_and_dlq(
    task_id: Optional[int],
    message_value: dict,
    error_msg: str,
    retry_count: int,
) -> None:
    if task_id is not None:
        await moderation_repository.update_task_failed(task_id, error_msg)
        await _cache_moderation_task(
            task_id, "failed", error_message=error_msg
        )
    await send_to_dlq(message_value, error_msg, retry_count)


async def process_message_with_retry(message_value: dict, retry_count: int = 0) -> None:
    item_id = message_value.get("item_id")
    task_id = message_value.get("task_id")

    if not item_id or task_id is None:
        error_msg = "В сообщении должны быть item_id и task_id"
        logger.error(error_msg)
        await send_to_dlq(message_value, error_msg, retry_count)
        return

    try:
        logger.info(
            f"Обработка task_id={task_id}, item_id={item_id} "
            f"(попытка {retry_count + 1}/{MAX_RETRIES})"
        )

        task = await moderation_repository.get_task_by_id(task_id)
        if not task:
            error_msg = f"Задача модерации task_id={task_id} не найдена"
            logger.error(error_msg)
            await send_to_dlq(message_value, error_msg, retry_count)
            return

        if task["item_id"] != item_id:
            error_msg = f"task_id={task_id} не соответствует item_id={item_id} в БД"
            logger.error(error_msg)
            await moderation_repository.update_task_failed(task_id, error_msg)
            await _cache_moderation_task(task_id, "failed", error_message=error_msg)
            await send_to_dlq(message_value, error_msg, retry_count)
            return

        item_data = await item_repository.get_item_by_item_id(item_id)
        if not item_data:
            error_msg = f"Объявление с item_id={item_id} не найдено"
            logger.error(error_msg)
            await moderation_repository.update_task_failed(task_id, error_msg)
            await _cache_moderation_task(task_id, "failed", error_message=error_msg)
            await send_to_dlq(message_value, error_msg, retry_count)
            return

        request = PredictionRequest(
            seller_id=item_data["seller_id"],
            is_verified_seller=item_data["is_verified_seller"],
            item_id=item_data["item_id"],
            name=item_data["name"],
            description=item_data["description"],
            category=item_data["category"],
            images_qty=item_data["images_qty"]
        )

        result = prediction_service.predict(request)

        await moderation_repository.update_task_completed(
            task_id,
            result.is_violation,
            result.probability
        )
        await _cache_moderation_task(
            task_id,
            "completed",
            is_violation=result.is_violation,
            probability=result.probability,
        )

        logger.info(
            f"Модерация завершена task_id={task_id}, item_id={item_id}, "
            f"is_violation={result.is_violation}"
        )

    except Exception as e:
        if is_retryable_error(e) and retry_count < MAX_RETRIES - 1:
            delay = retry_delay_seconds(retry_count)
            logger.warning(
                f"Временная ошибка task_id={task_id}, item_id={item_id}: {str(e)}. "
                f"Повтор через {delay} с (попытка {retry_count + 1}/{MAX_RETRIES})"
            )
            await asyncio.sleep(delay)
            await process_message_with_retry(message_value, retry_count + 1)
            return

        error_msg = f"Ошибка при обработке сообщения: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await _fail_task_and_dlq(task_id, message_value, error_msg, retry_count)


async def process_message(message_value: dict) -> None:
    await process_message_with_retry(message_value, retry_count=0)


async def consume_messages():
    await get_db_pool()

    use_mlflow = os.getenv("USE_MLFLOW", "false").lower() == "true"
    model = get_model(use_mlflow=use_mlflow)
    prediction_service.set_model(model)
    logger.info("Модель загружена в воркере")

    consumer = AIOKafkaConsumer(
        MODERATION_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        group_id="moderation_workers",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )

    await consumer.start()
    logger.info(f"Воркер запущен, подписка на топик {MODERATION_TOPIC}")

    try:
        async for message in consumer:
            logger.info(f"Получено сообщение из топика {MODERATION_TOPIC}: {message.value}")
            try:
                await process_message(message.value)
                await consumer.commit()
            except Exception as e:
                logger.error(
                    f"Необработанная ошибка при обработке сообщения: {str(e)}",
                    exc_info=True,
                )
    except Exception as e:
        logger.error(f"Ошибка в воркере: {str(e)}", exc_info=True)
    finally:
        await consumer.stop()
        await close_db_pool()


if __name__ == "__main__":
    try:
        asyncio.run(consume_messages())
    except KeyboardInterrupt:
        logger.info("Воркер остановлен")
