import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status

import routers.predictions as predictions_mod


class TestPredictEndpoint:

    @pytest.mark.asyncio
    async def test_predict_success_with_violation(self, client):
        with patch.object(
            predictions_mod.prediction_cache, "get_full_predict", new_callable=AsyncMock
        ) as mock_get, patch.object(
            predictions_mod.prediction_cache, "set_full_predict", new_callable=AsyncMock
        ) as mock_set:
            mock_get.return_value = None
            payload = {
            "seller_id": 12345,
            "is_verified_seller": False,
            "item_id": 67890,
            "name": "Товар",
            "description": "Короткое описание",
            "category": 1,
            "images_qty": 0
            }
            response = await client.post("/predict", json=payload)
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "is_violation" in data
            assert "probability" in data
            assert isinstance(data["is_violation"], bool)
            assert isinstance(data["probability"], float)
            assert 0.0 <= data["probability"] <= 1.0
            mock_set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_predict_cache_hit_skips_model(self, client):
        from models.predictions import PredictionResponse

        with patch.object(
            predictions_mod.prediction_cache, "get_full_predict", new_callable=AsyncMock
        ) as mock_get, patch.object(
            predictions_mod.prediction_cache, "set_full_predict", new_callable=AsyncMock
        ) as mock_set, patch.object(
            predictions_mod.prediction_service, "predict"
        ) as mock_predict:
            mock_get.return_value = PredictionResponse(
                is_violation=True, probability=0.99
            )
            payload = {
                "seller_id": 1,
                "is_verified_seller": False,
                "item_id": 1,
                "name": "X",
                "description": "Y",
                "category": 1,
                "images_qty": 0,
            }
            response = await client.post("/predict", json=payload)
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["probability"] == 0.99
            mock_predict.assert_not_called()
            mock_set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_predict_success_without_violation(self, client):
        with patch.object(
            predictions_mod.prediction_cache, "get_full_predict", new_callable=AsyncMock
        ) as mock_get, patch.object(
            predictions_mod.prediction_cache, "set_full_predict", new_callable=AsyncMock
        ) as mock_set:
            mock_get.return_value = None
            payload = {
            "seller_id": 12346,
            "is_verified_seller": True,
            "item_id": 67891,
            "name": "Товар",
            "description": "Описание товара",
            "category": 2,
            "images_qty": 5
            }
            response = await client.post("/predict", json=payload)
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "is_violation" in data
            assert "probability" in data
            assert isinstance(data["is_violation"], bool)
            assert isinstance(data["probability"], float)
            assert 0.0 <= data["probability"] <= 1.0
            mock_set.assert_awaited_once()

    @pytest.mark.parametrize("invalid_payload", [
        {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "description": "Описание",
            "category": 1,
            "images_qty": 5
        },
        {
            "seller_id": "not_an_int",
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "Товар",
            "description": "Описание",
            "category": 1,
            "images_qty": 5
        },
        {
            "seller_id": -1,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "Товар",
            "description": "Описание",
            "category": 1,
            "images_qty": 5
        },
        {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "",
            "description": "Описание",
            "category": 1,
            "images_qty": 5
        },
        {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "Товар",
            "description": "Описание",
            "category": 1,
            "images_qty": -1
        },
        {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "Товар",
            "description": "Описание",
            "category": -1,
            "images_qty": 5
        },
        {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "A" * 501,
            "description": "Описание",
            "category": 1,
            "images_qty": 5
        },
        {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "Товар",
            "description": "A" * 5001,
            "category": 1,
            "images_qty": 5
        },
        {},
        {
            "seller_id": 12345
        },
    ])
    @pytest.mark.asyncio
    async def test_predict_validation_errors(self, client, invalid_payload):
        with patch.object(
            predictions_mod.prediction_cache, "get_full_predict", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None
            response = await client.post("/predict", json=invalid_payload)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_predict_validation_missing_field_name(self, client):
        with patch.object(
            predictions_mod.prediction_cache, "get_full_predict", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None
            payload = {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "description": "Описание",
            "category": 1,
            "images_qty": 5
            }
            response = await client.post("/predict", json=payload)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert "name" in str(response.json()).lower()
