import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status

import routes.async_predict as async_predict_mod
from models.moderation import ModerationResultResponse


class TestAsyncPredictEndpoint:

    @pytest.mark.asyncio
    @patch.object(async_predict_mod, "send_moderation_request", new_callable=AsyncMock)
    async def test_async_predict_success(self, mock_send, client):
        with patch.object(
            async_predict_mod.item_repository, "get_item_by_item_id", new_callable=AsyncMock
        ) as mock_item, patch.object(
            async_predict_mod.moderation_repository, "create_task", new_callable=AsyncMock
        ) as mock_create:
            mock_item.return_value = {
                "seller_id": 101,
                "item_id": 201,
                "name": "Тестовый товар",
                "description": "Описание",
                "category": 1,
                "images_qty": 3,
            }
            mock_create.return_value = {"id": 55}
            response = await client.post("/async_predict?item_id=201")
            assert response.status_code == status.HTTP_202_ACCEPTED
            data = response.json()
            assert data["task_id"] == 55
            assert data["status"] == "pending"
            mock_send.assert_awaited_once_with(201, 55)

    @pytest.mark.asyncio
    async def test_async_predict_item_not_found(self, client):
        with patch.object(
            async_predict_mod.item_repository, "get_item_by_item_id", new_callable=AsyncMock
        ) as mock_item:
            mock_item.return_value = None
            response = await client.post("/async_predict?item_id=99999")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_async_predict_invalid_item_id(self, client):
        response = await client.post("/async_predict?item_id=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_async_predict_zero_item_id(self, client):
        response = await client.post("/async_predict?item_id=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @patch.object(async_predict_mod, "send_moderation_request", new_callable=AsyncMock)
    async def test_async_predict_kafka_error(self, mock_send, client):
        mock_send.side_effect = Exception("Kafka connection error")
        with patch.object(
            async_predict_mod.item_repository, "get_item_by_item_id", new_callable=AsyncMock
        ) as mock_item, patch.object(
            async_predict_mod.moderation_repository, "create_task", new_callable=AsyncMock
        ) as mock_create, patch.object(
            async_predict_mod.moderation_repository, "update_task_failed", new_callable=AsyncMock
        ) as mock_fail:
            mock_item.return_value = {
                "seller_id": 102,
                "item_id": 202,
                "name": "Товар",
                "description": "Описание",
                "category": 2,
                "images_qty": 5,
            }
            mock_create.return_value = {"id": 77}
            response = await client.post("/async_predict?item_id=202")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            mock_fail.assert_awaited()


class TestModerationResultEndpoint:

    @pytest.mark.asyncio
    async def test_get_moderation_result_cache_hit(self, client):
        with patch.object(
            async_predict_mod.prediction_cache, "get_moderation_result", new_callable=AsyncMock
        ) as mock_get, patch.object(
            async_predict_mod.prediction_cache, "set_moderation_result", new_callable=AsyncMock
        ) as mock_set, patch.object(
            async_predict_mod.moderation_repository, "get_task_by_id", new_callable=AsyncMock
        ) as mock_db:
            mock_get.return_value = ModerationResultResponse(
                task_id=10,
                status="completed",
                is_violation=False,
                probability=0.2,
                error_message=None,
            )
            response = await client.get("/moderation_result/10")
            assert response.status_code == status.HTTP_200_OK
            mock_db.assert_not_awaited()
            mock_set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_moderation_result_cache_miss(self, client):
        with patch.object(
            async_predict_mod.prediction_cache, "get_moderation_result", new_callable=AsyncMock
        ) as mock_get, patch.object(
            async_predict_mod.prediction_cache, "set_moderation_result", new_callable=AsyncMock
        ) as mock_set, patch.object(
            async_predict_mod.moderation_repository, "get_task_by_id", new_callable=AsyncMock
        ) as mock_db:
            mock_get.return_value = None
            mock_db.return_value = {
                "id": 11,
                "status": "pending",
                "is_violation": None,
                "probability": None,
                "error_message": None,
            }
            response = await client.get("/moderation_result/11")
            assert response.status_code == status.HTTP_200_OK
            mock_set.assert_awaited_once()
            assert mock_set.await_args[0][0] == 11

    @pytest.mark.asyncio
    async def test_get_moderation_result_not_found(self, client):
        with patch.object(
            async_predict_mod.prediction_cache, "get_moderation_result", new_callable=AsyncMock
        ) as mock_get, patch.object(
            async_predict_mod.moderation_repository, "get_task_by_id", new_callable=AsyncMock
        ) as mock_db:
            mock_get.return_value = None
            mock_db.return_value = None
            response = await client.get("/moderation_result/99999")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_moderation_result_invalid_task_id(self, client):
        response = await client.get("/moderation_result/-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
