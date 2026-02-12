import numpy as np
import logging
from typing import Optional
from models.predictions import PredictionRequest, PredictionResponse

logger = logging.getLogger(__name__)


class PredictionService:
    def __init__(self):
        self.model: Optional[object] = None
    
    def set_model(self, model):
        self.model = model
        logger.info("Модель установлена в сервисе")
    
    def _prepare_features(self, request: PredictionRequest) -> np.ndarray:
        is_verified = 1.0 if request.is_verified_seller else 0.0
        images_normalized = min(request.images_qty / 10.0, 1.0)
        description_length_normalized = min(len(request.description) / 1000.0, 1.0)
        category_normalized = min(request.category / 100.0, 1.0)
        
        features = np.array([[is_verified, images_normalized, description_length_normalized, category_normalized]])
        return features
    
    def predict(self, request: PredictionRequest) -> PredictionResponse:
        if self.model is None:
            logger.error("Модель не загружена")
            raise RuntimeError("Модель не загружена")
        
        logger.info(
            f"Получен запрос на предсказание: seller_id={request.seller_id}, "
            f"item_id={request.item_id}, is_verified_seller={request.is_verified_seller}, "
            f"images_qty={request.images_qty}, description_length={len(request.description)}, "
            f"category={request.category}"
        )
        
        try:
            features = self._prepare_features(request)
            logger.info(f"Подготовлены признаки для модели: {features[0]}")
            
            prediction = self.model.predict(features)[0]
            probability = self.model.predict_proba(features)[0][1]
            
            is_violation = bool(prediction)
            
            logger.info(
                f"Результат предсказания: seller_id={request.seller_id}, item_id={request.item_id}, "
                f"is_violation={is_violation}, probability={probability:.4f}"
            )
            
            return PredictionResponse(
                is_violation=is_violation,
                probability=float(probability)
            )
        except Exception as e:
            logger.error(f"Ошибка при предсказании: {str(e)}", exc_info=True)
            raise
