import json
import logging
import os
from datetime import datetime
from aiokafka import AIOKafkaProducer
from typing import Optional

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
MODERATION_TOPIC = "moderation"
DLQ_TOPIC = "moderation_dlq"

producer: Optional[AIOKafkaProducer] = None


async def get_producer() -> AIOKafkaProducer:
    global producer
    if producer is None:
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await producer.start()
        logger.info(f"Kafka producer подключен к {KAFKA_BOOTSTRAP_SERVERS}")
    return producer


async def close_producer():
    global producer
    if producer:
        await producer.stop()
        producer = None
        logger.info("Kafka producer отключен")


async def send_moderation_request(item_id: int) -> None:
    producer_instance = await get_producer()
    message = {
        "item_id": item_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    await producer_instance.send_and_wait(MODERATION_TOPIC, message)
    logger.info(f"Отправлено сообщение в топик {MODERATION_TOPIC} для item_id={item_id}")


async def send_to_dlq(original_message: dict, error: str, retry_count: int = 0) -> None:
    producer_instance = await get_producer()
    dlq_message = {
        "original_message": original_message,
        "error": error,
        "timestamp": datetime.utcnow().isoformat(),
        "retry_count": retry_count
    }
    await producer_instance.send_and_wait(DLQ_TOPIC, dlq_message)
    logger.error(f"Отправлено сообщение в DLQ {DLQ_TOPIC} после {retry_count + 1} попыток: {error}")
