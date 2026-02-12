import sys
from pathlib import Path
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from routers.predictions import prediction_service

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from main import app


class TestModelErrors:
    
    def test_predict_model_not_loaded(self):
        original_model = prediction_service.model
        prediction_service.model = None
        
        try:
            client = TestClient(app)
            payload = {
                "seller_id": 12345,
                "is_verified_seller": True,
                "item_id": 67890,
                "name": "Товар",
                "description": "Описание",
                "category": 1,
                "images_qty": 5
            }
            response = client.post("/predict", json=payload)
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert "модель" in response.json()["detail"].lower() or "model" in response.json()["detail"].lower()
        finally:
            prediction_service.model = original_model
