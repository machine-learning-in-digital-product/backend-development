import asyncio
import json
import logging
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from aiokafka import AIOKafkaConsumer
from database import get_db_pool, close_db_pool
from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultsRepository
from services.predictions import PredictionService
from models.predictions import PredictionRequest
from clients.kafka import send_to_dlq, DLQ_TOPIC
from model import get_model

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
MODERATION_TOPIC = "moderation"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "5"))

item_repository = ItemRepository()
moderation_repository = ModerationResultsRepository()
prediction_service = PredictionService()


def is_retryable_error(error: Exception) -> bool:
    if isinstance(error, RuntimeError):
        error_msg = str(error).lower()
        if "модель не загружена" in error_msg or "model" in error_msg:
            return True
    return False


async def process_message_with_retry(message_value: dict, retry_count: int = 0) -> None:
    item_id = message_value.get("item_id")
    if not item_id:
        error_msg = "item_id отсутствует в сообщении"
        logger.error(error_msg)
        await send_to_dlq(message_value, error_msg, retry_count)
        return
    
    try:
        logger.info(f"Обработка сообщения для item_id={item_id} (попытка {retry_count + 1}/{MAX_RETRIES})")
        
        item_data = await item_repository.get_item_by_item_id(item_id)
        
        tasks = await moderation_repository.get_tasks_by_item_id(item_id)
        if not tasks:
            error_msg = f"Задача модерации для item_id={item_id} не найдена"
            logger.error(error_msg)
            await send_to_dlq(message_value, error_msg, retry_count)
            return
        
        task = tasks[0]
        
        if not item_data:
            error_msg = f"Объявление с item_id={item_id} не найдено"
            logger.error(error_msg)
            await moderation_repository.update_task_failed(task["id"], error_msg)
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
            task["id"],
            result.is_violation,
            result.probability
        )
        
        logger.info(f"Модерация завершена для item_id={item_id}, is_violation={result.is_violation}")
        
    except RuntimeError as e:
        if is_retryable_error(e) and retry_count < MAX_RETRIES - 1:
            logger.warning(f"Временная ошибка при обработке item_id={item_id}: {str(e)}. Повтор через {RETRY_DELAY_SECONDS} секунд...")
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            await process_message_with_retry(message_value, retry_count + 1)
        else:
            error_msg = f"Модель не загружена: {str(e)}"
            logger.error(error_msg)
            
            tasks = await moderation_repository.get_tasks_by_item_id(item_id)
            if tasks:
                await moderation_repository.update_task_failed(tasks[0]["id"], error_msg)
            
            await send_to_dlq(message_value, error_msg, retry_count)
        
    except Exception as e:
        if is_retryable_error(e) and retry_count < MAX_RETRIES - 1:
            logger.warning(f"Временная ошибка при обработке item_id={item_id}: {str(e)}. Повтор через {RETRY_DELAY_SECONDS} секунд...")
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            await process_message_with_retry(message_value, retry_count + 1)
        else:
            error_msg = f"Ошибка при обработке сообщения: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            tasks = await moderation_repository.get_tasks_by_item_id(item_id)
            if tasks:
                await moderation_repository.update_task_failed(tasks[0]["id"], error_msg)
            
            await send_to_dlq(message_value, error_msg, retry_count)


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
        enable_auto_commit=True
    )
    
    await consumer.start()
    logger.info(f"Воркер запущен, подписка на топик {MODERATION_TOPIC}")
    
    try:
        async for message in consumer:
            logger.info(f"Получено сообщение из топика {MODERATION_TOPIC}: {message.value}")
            await process_message(message.value)
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
