import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status

import routers.simple_predict as simple_predict_mod
from models.predictions import PredictionResponse


class TestSimplePredictEndpoint:

    @pytest.mark.asyncio
    async def test_simple_predict_cache_hit(self, client):
        with patch.object(
            simple_predict_mod.prediction_cache, "get_simple_predict", new_callable=AsyncMock
        ) as mock_get, patch.object(
            simple_predict_mod.prediction_cache, "set_simple_predict", new_callable=AsyncMock
        ) as mock_set, patch.object(
            simple_predict_mod.item_repository, "get_item_by_item_id", new_callable=AsyncMock
        ) as mock_item:
            mock_get.return_value = PredictionResponse(
                is_violation=True, probability=0.42
            )
            response = await client.post("/simple_predict?item_id=201")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_violation"] is True
            assert data["probability"] == 0.42
            mock_item.assert_not_awaited()
            mock_set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_simple_predict_cache_miss_writes_cache(self, client):
        with patch.object(
            simple_predict_mod.prediction_cache, "get_simple_predict", new_callable=AsyncMock
        ) as mock_get, patch.object(
            simple_predict_mod.prediction_cache, "set_simple_predict", new_callable=AsyncMock
        ) as mock_set, patch.object(
            simple_predict_mod.item_repository, "get_item_by_item_id", new_callable=AsyncMock
        ) as mock_item:
            mock_get.return_value = None
            mock_item.return_value = {
                "seller_id": 101,
                "is_verified_seller": False,
                "item_id": 201,
                "name": "Товар",
                "description": "Описание",
                "category": 1,
                "images_qty": 0,
            }
            response = await client.post("/simple_predict?item_id=201")
            assert response.status_code == status.HTTP_200_OK
            mock_item.assert_awaited_once_with(201)
            assert mock_set.await_count == 1
            args = mock_set.await_args[0]
            assert args[0] == 201
            assert isinstance(args[1], PredictionResponse)

    @pytest.mark.asyncio
    async def test_simple_predict_item_not_found(self, client):
        with patch.object(
            simple_predict_mod.prediction_cache, "get_simple_predict", new_callable=AsyncMock
        ) as mock_get, patch.object(
            simple_predict_mod.item_repository, "get_item_by_item_id", new_callable=AsyncMock
        ) as mock_item:
            mock_get.return_value = None
            mock_item.return_value = None
            response = await client.post("/simple_predict?item_id=99999")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_simple_predict_invalid_item_id(self, client):
        response = await client.post("/simple_predict?item_id=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_simple_predict_zero_item_id(self, client):
        response = await client.post("/simple_predict?item_id=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
