from fastapi import APIRouter, HTTPException, status
from services.predictions import PredictionService
from models.predictions import PredictionRequest, PredictionResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

prediction_service = PredictionService()


@router.get('/predict', response_model=PredictionResponse, status_code=status.HTTP_200_OK)
async def predict(request: PredictionRequest) -> PredictionResponse:
    try:
        return prediction_service.predict(request)
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
