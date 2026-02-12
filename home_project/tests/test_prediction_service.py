import sys
from pathlib import Path
import pytest
import numpy as np
from sklearn.linear_model import LogisticRegression
from models.predictions import PredictionRequest, PredictionResponse
from services.predictions import PredictionService

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


class TestPredictionService:
    
    def setup_method(self):
        self.service = PredictionService()
        np.random.seed(42)
        X = np.random.rand(100, 4)
        y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
        y = y.astype(int)
        model = LogisticRegression()
        model.fit(X, y)
        self.service.set_model(model)
    
    def test_predict_success_with_violation(self):
        request = PredictionRequest(
            seller_id=1,
            is_verified_seller=False,
            item_id=100,
            name="Товар",
            description="Короткое",
            category=1,
            images_qty=0
        )
        result = self.service.predict(request)
        assert isinstance(result, PredictionResponse)
        assert isinstance(result.is_violation, bool)
        assert isinstance(result.probability, float)
        assert 0.0 <= result.probability <= 1.0
    
    def test_predict_success_without_violation(self):
        request = PredictionRequest(
            seller_id=2,
            is_verified_seller=True,
            item_id=200,
            name="Товар",
            description="Описание товара",
            category=2,
            images_qty=5
        )
        result = self.service.predict(request)
        assert isinstance(result, PredictionResponse)
        assert isinstance(result.is_violation, bool)
        assert isinstance(result.probability, float)
        assert 0.0 <= result.probability <= 1.0
    
    def test_predict_model_not_loaded(self):
        service = PredictionService()
        request = PredictionRequest(
            seller_id=1,
            is_verified_seller=True,
            item_id=100,
            name="Товар",
            description="Описание",
            category=1,
            images_qty=5
        )
        with pytest.raises(RuntimeError, match="Модель не загружена"):
            service.predict(request)
    
    def test_prepare_features(self):
        request = PredictionRequest(
            seller_id=1,
            is_verified_seller=True,
            item_id=100,
            name="Товар",
            description="A" * 500,
            category=50,
            images_qty=5
        )
        features = self.service._prepare_features(request)
        assert features.shape == (1, 4)
        assert features[0][0] == 1.0
        assert features[0][1] == 0.5
        assert features[0][2] == 0.5
        assert features[0][3] == 0.5
    
    def test_prepare_features_normalization(self):
        request = PredictionRequest(
            seller_id=1,
            is_verified_seller=False,
            item_id=100,
            name="Товар",
            description="A" * 2000,
            category=200,
            images_qty=20
        )
        features = self.service._prepare_features(request)
        assert features[0][0] == 0.0
        assert features[0][1] == 1.0
        assert features[0][2] == 1.0
        assert features[0][3] == 1.0
