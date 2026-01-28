from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    seller_id: int = Field(..., description="Идентификатор продавца", gt=0)
    is_verified_seller: bool = Field(..., description="Статус подтверждения продавца")
    item_id: int = Field(..., description="Идентификатор товара", gt=0)
    name: str = Field(..., description="Название товара", min_length=1, max_length=500)
    description: str = Field(..., description="Описание товара", min_length=0, max_length=5000)
    category: int = Field(..., description="Категория товара", ge=0)
    images_qty: int = Field(..., description="Количество изображений товара", ge=0)
