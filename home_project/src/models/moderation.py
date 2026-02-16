from pydantic import BaseModel, Field
from typing import Optional


class AsyncPredictResponse(BaseModel):
    task_id: int = Field(..., description="ID задачи модерации")
    status: str = Field(..., description="Статус задачи")
    message: str = Field(..., description="Сообщение")


class ModerationResultResponse(BaseModel):
    task_id: int = Field(..., description="ID задачи модерации")
    status: str = Field(..., description="Статус задачи")
    is_violation: Optional[bool] = Field(None, description="Результат модерации")
    probability: Optional[float] = Field(None, description="Вероятность нарушения")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
