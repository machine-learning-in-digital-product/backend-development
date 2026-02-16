import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from routers.predictions import router as prediction_router, prediction_service
from routers.simple_predict import router as simple_predict_router
from routers.async_predict import router as async_predict_router
from model import get_model, train_model, register_model_in_mlflow
from database import get_db_pool, close_db_pool
from clients.kafka import get_producer, close_producer
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
        await get_db_pool()
        logger.info("Подключение к базе данных установлено")
        
        await get_producer()
        logger.info("Kafka producer подключен")
        
        register_model = os.getenv("REGISTER_MODEL", "false").lower() == "true"
        use_mlflow = os.getenv("USE_MLFLOW", "false").lower() == "true"
        
        if register_model:
            logger.info("Регистрация модели в MLflow...")
            model = train_model()
            register_model_in_mlflow(model, model_name="moderation-model")
            logger.info("Модель успешно зарегистрирована в MLflow!")
            logger.info("Запустите MLflow UI: mlflow ui --backend-store-uri sqlite:///mlflow.db")
        
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
    
    await close_producer()
    await close_db_pool()
    logger.info("Завершение работы приложения")


app = FastAPI(lifespan=lifespan)
app.include_router(prediction_router)
app.include_router(simple_predict_router)
app.include_router(async_predict_router)



@app.get("/")
async def root():
    return {'message': 'Hello World'}



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
