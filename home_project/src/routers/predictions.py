from fastapi import APIRouter
from services.predictions import PredictionService
from models.predictions import PredictionRequest
from fastapi import status

router = APIRouter()

prediction_service = PredictionService()

@router.post('/predict', status_code=status.HTTP_200_OK)
async def predict(request: PredictionRequest) -> bool:
    return prediction_service.predict(request)
