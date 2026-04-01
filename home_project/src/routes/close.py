from fastapi import APIRouter, HTTPException, status

from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultsRepository
from storage.prediction_cache import prediction_cache

router = APIRouter()

item_repository = ItemRepository()
moderation_repository = ModerationResultsRepository()


@router.post("/close", status_code=status.HTTP_200_OK)
async def close_item(item_id: int) -> dict:
    if item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="item_id должен быть положительным числом",
        )

    tasks = await moderation_repository.get_tasks_by_item_id(item_id)
    task_ids = [t["id"] for t in tasks]

    deleted = await item_repository.delete_item_by_item_id(item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Объявление с item_id={item_id} не найдено",
        )

    await prediction_cache.invalidate_item(item_id, task_ids)
    return {"item_id": item_id, "closed": True}
