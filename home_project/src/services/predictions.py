from models.predictions import PredictionRequest


class PredictionService:
    def predict(self, request: PredictionRequest) -> bool:
        if request.is_verified_seller:
            return True
        
        return request.images_qty > 0
