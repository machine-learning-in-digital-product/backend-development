from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status

import routers.close as close_router_mod
from models.predictions import PredictionResponse
from models.moderation import ModerationResultResponse
from repositories.items import ItemRepository
from repositories.moderation_results import ModerationResultsRepository
from repositories.users import UserRepository
from storage.prediction_cache import PredictionCacheStorage


class TestCloseUnit:

    @pytest.mark.asyncio
    async def test_close_success_invalidates_cache(self, client):
        with patch.object(
            close_router_mod.moderation_repository, "get_tasks_by_item_id", new_callable=AsyncMock
        ) as mock_tasks, patch.object(
            close_router_mod.item_repository, "delete_item_by_item_id", new_callable=AsyncMock
        ) as mock_del, patch.object(
            close_router_mod.prediction_cache, "invalidate_item", new_callable=AsyncMock
        ) as mock_inv:
            mock_tasks.return_value = [{"id": 3}, {"id": 4}]
            mock_del.return_value = True
            response = await client.post("/close?item_id=10")
            assert response.status_code == status.HTTP_200_OK
            mock_tasks.assert_awaited_once_with(10)
            mock_del.assert_awaited_once_with(10)
            mock_inv.assert_awaited_once_with(10, [3, 4])

    @pytest.mark.asyncio
    async def test_close_not_found(self, client):
        with patch.object(
            close_router_mod.moderation_repository, "get_tasks_by_item_id", new_callable=AsyncMock
        ) as mock_tasks, patch.object(
            close_router_mod.item_repository, "delete_item_by_item_id", new_callable=AsyncMock
        ) as mock_del, patch.object(
            close_router_mod.prediction_cache, "invalidate_item", new_callable=AsyncMock
        ) as mock_inv:
            mock_tasks.return_value = []
            mock_del.return_value = False
            response = await client.post("/close?item_id=999")
            assert response.status_code == status.HTTP_404_NOT_FOUND
            mock_inv.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_close_invalid_item_id(self, client):
        response = await client.post("/close?item_id=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
@pytest.mark.usefixtures("db_pool")
class TestCloseIntegration:

    @pytest.mark.asyncio
    async def test_close_removes_postgres_and_redis(
        self, integration_client, integration_redis
    ):
        user_repo = UserRepository()
        await user_repo.create_user(seller_id=500, is_verified_seller=True)
        item_repo = ItemRepository()
        await item_repo.create_item(
            item_id=600,
            seller_id=500,
            name="К закрытию",
            description="Текст",
            category=1,
            images_qty=2,
        )
        mod_repo = ModerationResultsRepository()
        task = await mod_repo.create_task(600)
        task_id = task["id"]

        storage = PredictionCacheStorage()
        await storage.set_simple_predict(
            600, PredictionResponse(is_violation=False, probability=0.05)
        )
        await storage.set_moderation_result(
            task_id,
            ModerationResultResponse(
                task_id=task_id,
                status="pending",
                is_violation=None,
                probability=None,
                error_message=None,
            ),
        )

        response = await integration_client.post("/close?item_id=600")
        assert response.status_code == status.HTTP_200_OK

        assert await item_repo.get_item_by_item_id(600) is None
        assert await mod_repo.get_task_by_id(task_id) is None
        assert await storage.get_simple_predict(600) is None
        assert await storage.get_moderation_result(task_id) is None
