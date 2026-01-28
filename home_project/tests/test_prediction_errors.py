import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from models.predictions import PredictionRequest
from services.predictions import PredictionService


class TestPredictionServiceErrors:
    
    def setup_method(self):
        self.service = PredictionService()
    
    def test_predict_handles_none_values_gracefully(self):
        with pytest.raises(ValidationError):
            PredictionRequest(
                seller_id=None,
                is_verified_seller=True,
                item_id=100,
                name="Товар",
                description="Описание",
                category=1,
                images_qty=5
            )
    
    def test_predict_handles_edge_case_zero_images(self):
        request = PredictionRequest(
            seller_id=1,
            is_verified_seller=False,
            item_id=100,
            name="Товар",
            description="Описание",
            category=1,
            images_qty=0
        )
        result = self.service.predict(request)
        assert isinstance(result, bool)
        assert result is False
    
    def test_predict_handles_large_values(self):
        request = PredictionRequest(
            seller_id=999999999,
            is_verified_seller=True,
            item_id=999999999,
            name="Товар",
            description="Описание",
            category=999999999,
            images_qty=999999999
        )
        result = self.service.predict(request)
        assert isinstance(result, bool)
        assert result is True
    
    def test_predict_handles_boolean_edge_cases(self):
        request_true = PredictionRequest(
            seller_id=1,
            is_verified_seller=True,
            item_id=100,
            name="Товар",
            description="Описание",
            category=1,
            images_qty=0
        )
        result_true = self.service.predict(request_true)
        assert result_true is True
        
        request_false = PredictionRequest(
            seller_id=2,
            is_verified_seller=False,
            item_id=200,
            name="Товар",
            description="Описание",
            category=2,
            images_qty=0
        )
        result_false = self.service.predict(request_false)
        assert result_false is False
    
    def test_predict_service_always_returns_boolean(self):
        test_cases = [
            {"is_verified_seller": True, "images_qty": 0},
            {"is_verified_seller": True, "images_qty": 10},
            {"is_verified_seller": False, "images_qty": 0},
            {"is_verified_seller": False, "images_qty": 1},
            {"is_verified_seller": False, "images_qty": 100},
        ]
        
        for case in test_cases:
            request = PredictionRequest(
                seller_id=1,
                is_verified_seller=case["is_verified_seller"],
                item_id=100,
                name="Товар",
                description="Описание",
                category=1,
                images_qty=case["images_qty"]
            )
            result = self.service.predict(request)
            assert isinstance(result, bool), f"Результат должен быть bool, получен {type(result)}"
            assert result in [True, False]
