import pytest
import asyncio
from fastapi import status
from conftest import client, db_pool
from repositories.users import UserRepository
from repositories.items import ItemRepository


class TestSimplePredictEndpoint:
    
    @pytest.mark.asyncio
    async def test_simple_predict_success_with_violation(self, client, db_pool):
        user_repo = UserRepository()
        item_repo = ItemRepository()
        
        await user_repo.create_user(seller_id=101, is_verified_seller=False)
        await item_repo.create_item(
            item_id=201,
            seller_id=101,
            name="Товар без изображений",
            description="Короткое описание",
            category=1,
            images_qty=0
        )
        
        response = client.post("/simple_predict?item_id=201")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "is_violation" in data
        assert "probability" in data
        assert isinstance(data["is_violation"], bool)
        assert isinstance(data["probability"], float)
        assert 0.0 <= data["probability"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_simple_predict_success_without_violation(self, client, db_pool):
        user_repo = UserRepository()
        item_repo = ItemRepository()
        
        await user_repo.create_user(seller_id=102, is_verified_seller=True)
        await item_repo.create_item(
            item_id=202,
            seller_id=102,
            name="Товар с изображениями",
            description="Описание товара",
            category=2,
            images_qty=5
        )
        
        response = client.post("/simple_predict?item_id=202")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "is_violation" in data
        assert "probability" in data
        assert isinstance(data["is_violation"], bool)
        assert isinstance(data["probability"], float)
        assert 0.0 <= data["probability"] <= 1.0
    
    def test_simple_predict_item_not_found(self, client):
        response = client.post("/simple_predict?item_id=99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "не найдено" in response.json()["detail"].lower() or "not found" in response.json()["detail"].lower()
    
    def test_simple_predict_invalid_item_id(self, client):
        response = client.post("/simple_predict?item_id=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_simple_predict_zero_item_id(self, client):
        response = client.post("/simple_predict?item_id=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
