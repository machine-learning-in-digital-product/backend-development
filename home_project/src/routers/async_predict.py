from fastapi import APIRouter, HTTPException, status
from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultsRepository
from models.moderation import AsyncPredictResponse, ModerationResultResponse
from clients.kafka import send_moderation_request
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

item_repository = ItemRepository()
moderation_repository = ModerationResultsRepository()


@router.post('/async_predict', response_model=AsyncPredictResponse, status_code=status.HTTP_202_ACCEPTED)
async def async_predict(item_id: int) -> AsyncPredictResponse:
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
    
    task = await moderation_repository.create_task(item_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании задачи модерации"
        )
    
    try:
        await send_moderation_request(item_id)
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения в Kafka: {str(e)}", exc_info=True)
        await moderation_repository.update_task_failed(task["id"], f"Ошибка отправки в Kafka: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при отправке запроса на модерацию: {str(e)}"
        )
    
    return AsyncPredictResponse(
        task_id=task["id"],
        status="pending",
        message="Moderation request accepted"
    )


@router.get('/moderation_result/{task_id}', response_model=ModerationResultResponse)
async def get_moderation_result(task_id: int) -> ModerationResultResponse:
    if task_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="task_id должен быть положительным числом"
        )
    
    task = await moderation_repository.get_task_by_id(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задача с task_id={task_id} не найдена"
        )
    
    return ModerationResultResponse(
        task_id=task["id"],
        status=task["status"],
        is_violation=task["is_violation"],
        probability=task["probability"],
        error_message=task["error_message"]
    )
