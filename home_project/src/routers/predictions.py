from fastapi import APIRouter, HTTPException, status
from services.predictions import PredictionService
from models.predictions import PredictionRequest, PredictionResponse
from storage.prediction_cache import prediction_cache
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

prediction_service = PredictionService()


@router.post('/predict', response_model=PredictionResponse, status_code=status.HTTP_200_OK)
async def predict(request: PredictionRequest) -> PredictionResponse:
    cached = await prediction_cache.get_full_predict(request)
    if cached is not None:
        return cached
    try:
        result = prediction_service.predict(request)
        await prediction_cache.set_full_predict(request, result)
        return result
    except RuntimeError as e:
        logger.error(f"Модель не загружена: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Модель не загружена. Сервис временно недоступен."
        )
    except Exception as e:
        logger.error(f"Ошибка при предсказании: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при предсказании: {str(e)}"
        )
