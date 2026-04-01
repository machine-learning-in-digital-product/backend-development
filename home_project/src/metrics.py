import time
from typing import TypeVar, Awaitable

from prometheus_client import Counter, Histogram

T = TypeVar("T")

PREDICTIONS_TOTAL = Counter(
    "predictions_total",
    "Общее число предсказаний модели",
    ["result"],
)

PREDICTION_DURATION_SECONDS = Histogram(
    "prediction_duration_seconds",
    "Длительность инференса ML-модели (predict + predict_proba)",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

PREDICTION_ERRORS_TOTAL = Counter(
    "prediction_errors_total",
    "Ошибки при предсказании",
    ["error_type"],
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "db_query_duration_seconds",
    "Длительность запросов к PostgreSQL",
    ["query_type"],
    buckets=(0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

MODEL_PREDICTION_PROBABILITY = Histogram(
    "model_prediction_probability",
    "Распределение вероятности нарушения по ответам модели",
    buckets=(0.0, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0),
)


async def record_db_query(query_type: str, awaitable: Awaitable[T]) -> T:
    start = time.perf_counter()
    try:
        return await awaitable
    finally:
        DB_QUERY_DURATION_SECONDS.labels(query_type=query_type).observe(
            time.perf_counter() - start
        )
