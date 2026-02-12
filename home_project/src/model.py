import numpy as np
from sklearn.linear_model import LogisticRegression
import pickle
import os
import logging

logger = logging.getLogger(__name__)


def train_model():
    logger.info("Обучение модели на синтетических данных...")
    np.random.seed(42)
    X = np.random.rand(1000, 4)
    y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
    y = y.astype(int)
    
    model = LogisticRegression()
    model.fit(X, y)
    logger.info("Модель успешно обучена")
    return model


def save_model(model, path="model.pkl"):
    logger.info(f"Сохранение модели в {path}")
    with open(path, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"Модель сохранена в {path}")


def load_model(path="model.pkl"):
    logger.info(f"Загрузка модели из {path}")
    with open(path, "rb") as f:
        model = pickle.load(f)
    logger.info(f"Модель загружена из {path}")
    return model


def get_or_train_model(model_path="model.pkl"):
    if os.path.exists(model_path):
        logger.info(f"Файл модели {model_path} найден, загружаем модель")
        return load_model(model_path)
    else:
        logger.info(f"Файл модели {model_path} не найден, обучаем новую модель")
        model = train_model()
        save_model(model, model_path)
        return model


def register_model_in_mlflow(model, model_name="moderation-model"):
    try:
        import mlflow
        from mlflow.sklearn import log_model
        
        mlflow.set_tracking_uri("sqlite:///mlflow.db")
        mlflow.set_experiment("moderation-model")
        
        with mlflow.start_run():
            log_model(model, "model", registered_model_name=model_name)
        logger.info(f"Модель {model_name} зарегистрирована в MLflow")
    except ImportError:
        logger.warning("MLflow не установлен, пропускаем регистрацию модели")
    except Exception as e:
        logger.error(f"Ошибка при регистрации модели в MLflow: {str(e)}", exc_info=True)


def load_model_from_mlflow(model_name="moderation-model", stage="Production"):
    try:
        import mlflow
        
        model_uri = f"models:/{model_name}/{stage}"
        logger.info(f"Загрузка модели из MLflow: {model_uri}")
        model = mlflow.sklearn.load_model(model_uri)
        logger.info(f"Модель успешно загружена из MLflow")
        return model
    except ImportError:
        logger.error("MLflow не установлен")
        raise RuntimeError("MLflow не установлен")
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели из MLflow: {str(e)}", exc_info=True)
        raise


def get_model(use_mlflow=False, model_name="moderation-model", model_path="model.pkl"):
    if use_mlflow:
        try:
            return load_model_from_mlflow(model_name)
        except Exception as e:
            logger.warning(f"Не удалось загрузить модель из MLflow: {str(e)}, используем локальную модель")
            return get_or_train_model(model_path)
    else:
        return get_or_train_model(model_path)
