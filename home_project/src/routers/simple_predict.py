from fastapi import APIRouter, HTTPException, status
from services.predictions import PredictionService
from models.predictions import PredictionRequest, PredictionResponse
from repositories.items import ItemRepository
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

prediction_service = PredictionService()
item_repository = ItemRepository()


@router.post('/simple_predict', response_model=PredictionResponse, status_code=status.HTTP_200_OK)
async def simple_predict(item_id: int) -> PredictionResponse:
    if item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="item_id должен быть положительным числом"
        )
    
    item_data = await item_repository.get_item_by_item_id(item_id)
    
    if not item_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Объявление с item_id={item_id} не найдено"
        )
    
    request = PredictionRequest(
        seller_id=item_data["seller_id"],
        is_verified_seller=item_data["is_verified_seller"],
        item_id=item_data["item_id"],
        name=item_data["name"],
        description=item_data["description"],
        category=item_data["category"],
        images_qty=item_data["images_qty"]
    )
    
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
