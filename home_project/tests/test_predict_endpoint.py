import pytest
from fastapi import status
from conftest import client


class TestPredictEndpoint:
    
    def test_predict_verified_seller_success(self, client):
        payload = {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "Смартфон iPhone 15",
            "description": "Новый смартфон в отличном состоянии",
            "category": 1,
            "images_qty": 0
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() is True
    
    def test_predict_unverified_seller_with_images_success(self, client):
        payload = {
            "seller_id": 12346,
            "is_verified_seller": False,
            "item_id": 67891,
            "name": "Ноутбук MacBook Pro",
            "description": "Отличное состояние",
            "category": 2,
            "images_qty": 5
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() is True
    
    def test_predict_unverified_seller_without_images_failure(self, client):
        payload = {
            "seller_id": 12347,
            "is_verified_seller": False,
            "item_id": 67892,
            "name": "Планшет iPad",
            "description": "Без изображений",
            "category": 3,
            "images_qty": 0
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() is False
    
    def test_predict_validation_missing_field(self, client):
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
    
    def test_predict_validation_wrong_type(self, client):
        payload = {
            "seller_id": "not_an_int",
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "Товар",
            "description": "Описание",
            "category": 1,
            "images_qty": 5
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_predict_validation_negative_seller_id(self, client):
        payload = {
            "seller_id": -1,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "Товар",
            "description": "Описание",
            "category": 1,
            "images_qty": 5
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_predict_validation_empty_name(self, client):
        payload = {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "",
            "description": "Описание",
            "category": 1,
            "images_qty": 5
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_predict_validation_negative_images_qty(self, client):
        payload = {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "Товар",
            "description": "Описание",
            "category": 1,
            "images_qty": -1
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_predict_validation_negative_category(self, client):
        payload = {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "Товар",
            "description": "Описание",
            "category": -1,
            "images_qty": 5
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_predict_validation_name_too_long(self, client):
        payload = {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "A" * 501,
            "description": "Описание",
            "category": 1,
            "images_qty": 5
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_predict_validation_description_too_long(self, client):
        payload = {
            "seller_id": 12345,
            "is_verified_seller": True,
            "item_id": 67890,
            "name": "Товар",
            "description": "A" * 5001,
            "category": 1,
            "images_qty": 5
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_predict_empty_request(self, client):
        response = client.post("/predict", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_predict_all_fields_required(self, client):
        payload = {
            "seller_id": 12345
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
