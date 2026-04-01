import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from metrics import (
    DB_QUERY_DURATION_SECONDS,
    MODEL_PREDICTION_PROBABILITY,
    PREDICTION_DURATION_SECONDS,
    PREDICTION_ERRORS_TOTAL,
    PREDICTIONS_TOTAL,
    record_db_query,
)

__all__ = [
    "DB_QUERY_DURATION_SECONDS",
    "MODEL_PREDICTION_PROBABILITY",
    "PREDICTION_DURATION_SECONDS",
    "PREDICTION_ERRORS_TOTAL",
    "PREDICTIONS_TOTAL",
    "record_db_query",
]
