import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status

import routers.predictions as predictions_mod
from routers.predictions import prediction_service


class TestModelErrors:

    @pytest.mark.asyncio
    async def test_predict_model_not_loaded(self, client):
        original_model = prediction_service.model
        prediction_service.model = None

        try:
            with patch.object(
                predictions_mod.prediction_cache, "get_full_predict", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = None
                payload = {
                    "seller_id": 12345,
                    "is_verified_seller": True,
                    "item_id": 67890,
                    "name": "Товар",
                    "description": "Описание",
                    "category": 1,
                    "images_qty": 5,
                }
                response = await client.post("/predict", json=payload)
                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                assert (
                    "модель" in response.json()["detail"].lower()
                    or "model" in response.json()["detail"].lower()
                )
        finally:
            prediction_service.model = original_model
