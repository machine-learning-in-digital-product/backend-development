from contextlib import asynccontextmanager
from fastapi import FastAPI
from routers.predictions import router as prediction_router, prediction_service
from model import get_model
import logging
import os
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск приложения, загрузка модели...")
    try:
        use_mlflow = os.getenv("USE_MLFLOW", "false").lower() == "true"
        if use_mlflow:
            logger.info("Используется MLflow для загрузки модели")
        else:
            logger.info("Используется локальный файл для загрузки модели")
        
        model = get_model(use_mlflow=use_mlflow)
        prediction_service.set_model(model)
        logger.info("Модель успешно загружена и установлена в сервисе")
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели: {str(e)}", exc_info=True)
        raise
    
    yield
    
    logger.info("Завершение работы приложения")


app = FastAPI(lifespan=lifespan)
app.include_router(prediction_router)


@app.get("/")
async def root():
    return {'message': 'Hello World'}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
