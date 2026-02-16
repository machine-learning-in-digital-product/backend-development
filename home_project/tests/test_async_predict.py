import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi import status
from conftest import client, db_pool
from repositories.users import UserRepository
from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultsRepository


class TestAsyncPredictEndpoint:
    
    @pytest.mark.asyncio
    @patch('routers.async_predict.send_moderation_request')
    async def test_async_predict_success(self, mock_send, client, db_pool):
        mock_send.return_value = None
        
        user_repo = UserRepository()
        item_repo = ItemRepository()
        
        await user_repo.create_user(seller_id=101, is_verified_seller=False)
        await item_repo.create_item(
            item_id=201,
            seller_id=101,
            name="Тестовый товар",
            description="Описание",
            category=1,
            images_qty=3
        )
        
        response = client.post("/async_predict?item_id=201")
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert data["message"] == "Moderation request accepted"
        assert isinstance(data["task_id"], int)
        assert data["task_id"] > 0
        
        mock_send.assert_called_once_with(201)
    
    @pytest.mark.asyncio
    async def test_async_predict_item_not_found(self, client, db_pool):
        response = client.post("/async_predict?item_id=99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "не найдено" in response.json()["detail"].lower() or "not found" in response.json()["detail"].lower()
    
    def test_async_predict_invalid_item_id(self, client):
        response = client.post("/async_predict?item_id=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_async_predict_zero_item_id(self, client):
        response = client.post("/async_predict?item_id=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    @patch('routers.async_predict.send_moderation_request')
    async def test_async_predict_kafka_error(self, mock_send, client, db_pool):
        mock_send.side_effect = Exception("Kafka connection error")
        
        user_repo = UserRepository()
        item_repo = ItemRepository()
        
        await user_repo.create_user(seller_id=102, is_verified_seller=True)
        await item_repo.create_item(
            item_id=202,
            seller_id=102,
            name="Товар",
            description="Описание",
            category=2,
            images_qty=5
        )
        
        response = client.post("/async_predict?item_id=202")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        moderation_repo = ModerationResultsRepository()
        tasks = await moderation_repo.get_tasks_by_item_id(202)
        assert len(tasks) > 0
        assert tasks[0]["status"] == "failed"


class TestModerationResultEndpoint:
    
    @pytest.mark.asyncio
    async def test_get_moderation_result_pending(self, client, db_pool):
        user_repo = UserRepository()
        item_repo = ItemRepository()
        moderation_repo = ModerationResultsRepository()
        
        await user_repo.create_user(seller_id=103, is_verified_seller=False)
        await item_repo.create_item(
            item_id=203,
            seller_id=103,
            name="Товар",
            description="Описание",
            category=1,
            images_qty=2
        )
        
        task = await moderation_repo.create_task(203)
        task_id = task["id"]
        
        response = client.get(f"/moderation_result/{task_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "pending"
        assert data["is_violation"] is None
        assert data["probability"] is None
    
    @pytest.mark.asyncio
    async def test_get_moderation_result_completed(self, client, db_pool):
        user_repo = UserRepository()
        item_repo = ItemRepository()
        moderation_repo = ModerationResultsRepository()
        
        await user_repo.create_user(seller_id=104, is_verified_seller=True)
        await item_repo.create_item(
            item_id=204,
            seller_id=104,
            name="Товар",
            description="Описание",
            category=2,
            images_qty=5
        )
        
        task = await moderation_repo.create_task(204)
        task_id = task["id"]
        
        await moderation_repo.update_task_completed(task_id, False, 0.15)
        
        response = client.get(f"/moderation_result/{task_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "completed"
        assert data["is_violation"] is False
        assert data["probability"] == 0.15
    
    @pytest.mark.asyncio
    async def test_get_moderation_result_failed(self, client, db_pool):
        user_repo = UserRepository()
        item_repo = ItemRepository()
        moderation_repo = ModerationResultsRepository()
        
        await user_repo.create_user(seller_id=105, is_verified_seller=False)
        await item_repo.create_item(
            item_id=205,
            seller_id=105,
            name="Товар",
            description="Описание",
            category=1,
            images_qty=1
        )
        
        task = await moderation_repo.create_task(205)
        task_id = task["id"]
        
        await moderation_repo.update_task_failed(task_id, "Модель недоступна")
        
        response = client.get(f"/moderation_result/{task_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "failed"
        assert data["error_message"] == "Модель недоступна"
    
    def test_get_moderation_result_not_found(self, client):
        response = client.get("/moderation_result/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_moderation_result_invalid_task_id(self, client):
        response = client.get("/moderation_result/-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
