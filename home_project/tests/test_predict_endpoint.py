import pytest
from fastapi import status
from conftest import client


class TestPredictEndpoint:
    
    def test_predict_success_with_violation(self, client):
        payload = {
            "seller_id": 12345,
            "is_verified_seller": False,
            "item_id": 67890,
            "name": "Товар",
            "description": "Короткое описание",
            "category": 1,
            "images_qty": 0
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "is_violation" in data
        assert "probability" in data
        assert isinstance(data["is_violation"], bool)
        assert isinstance(data["probability"], float)
        assert 0.0 <= data["probability"] <= 1.0
    
    def test_predict_success_without_violation(self, client):
        payload = {
            "seller_id": 12346,
            "is_verified_seller": True,
            "item_id": 67891,
            "name": "Товар",
            "description": "Описание товара",
            "category": 2,
            "images_qty": 5
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "is_violation" in data
        assert "probability" in data
        assert isinstance(data["is_violation"], bool)
        assert isinstance(data["probability"], float)
        assert 0.0 <= data["probability"] <= 1.0
    
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
    def test_predict_validation_errors(self, client, invalid_payload):
        response = client.post("/predict", json=invalid_payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_predict_validation_missing_field_name(self, client):
        payload = {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "description": "Описание",
            "category": 1,
            "images_qty": 5
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "name" in str(response.json()).lower()
