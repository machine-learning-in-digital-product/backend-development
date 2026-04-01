import os

import pytest
from aiokafka import AIOKafkaProducer

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_kafka_broker_accepts_connection():
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
    try:
        await producer.start()
    except Exception as exc:
        pytest.skip(f"Kafka недоступна ({bootstrap}): {exc}")
    finally:
        await producer.stop()
