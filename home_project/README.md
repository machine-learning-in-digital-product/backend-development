# Сервис модерации объявлений

FastAPI-сервис с ML-моделью (Logistic Regression), PostgreSQL, Kafka (Redpanda), Redis, Prometheus, Grafana, MLflow и JWT-авторизацией.

## Структура проекта

```
home_project/
├── src/
│   ├── routes/              # HTTP-эндпоинты
│   ├── services/            # бизнес-логика (предсказания, JWT)
│   ├── repositories/        # доступ к БД (сырой SQL через asyncpg)
│   ├── models/              # Pydantic-модели
│   ├── clients/             # kafka, redis, postgres (пул asyncpg)
│   ├── storage/             # кэш предсказаний (Redis)
│   ├── workers/             # Kafka consumer
│   ├── dependencies/        # FastAPI Depends (авторизация)
│   ├── middleware/          # метрики Prometheus
│   └── main.py
├── migrations/              # SQL-миграции
├── tests/
├── docker-compose.yml
├── prometheus.yml
└── requirements.txt
```

ORM не используется: только чистый SQL в репозиториях.

## Запуск инфраструктуры (Docker)

Из каталога `home_project`:

```bash
docker compose up -d
```

Поднимаются: **PostgreSQL** (5432), **Redpanda/Kafka** (9092), **Redis** (6379), **Prometheus** (9090), **Grafana** (3000, admin/admin), **MLflow** (5000), консоль Redpanda (8080).

Применить миграции:

```bash
export DATABASE_URL=postgresql://moderation_user:moderation_password@localhost:5432/moderation_db
python run_migrations.py
```

## Запуск API

Нужен Python 3.10+.

```bash
cd home_project
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Переменные окружения (типовые):

| Переменная | Назначение | Пример |
|------------|------------|--------|
| `DATABASE_URL` | PostgreSQL | `postgresql://moderation_user:moderation_password@localhost:5432/moderation_db` |
| `REDIS_URL` | Кэш | `redis://localhost:6379/0` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka | `localhost:9092` |
| `MLFLOW_TRACKING_URI` | MLflow Registry | `http://127.0.0.1:5000` |
| `USE_MLFLOW` | Загрузка модели из MLflow | `true` / `false` |
| `JWT_SECRET` | Подпись JWT (≥32 символов) | свой секрет |
| `TESTING` | Отключает Kafka producer в тестах | `1` только для pytest |

Запуск приложения (модель ищется в `model.pkl` или обучается при отсутствии файла):

```bash
cd src
JWT_SECRET="your-32-byte-or-longer-secret-here!!!" \
REDIS_URL=redis://localhost:6379/0 \
KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
uvicorn main:app --host 0.0.0.0 --port 8003
```

Для MLflow с Docker:

```bash
export MLFLOW_TRACKING_URI=http://localhost:5000
```

Регистрация модели в реестре (один раз, при необходимости):

```bash
export REGISTER_MODEL=true
# затем запуск uvicorn — в коде вызывается register_model_in_mlflow
```

Prometheus собирает метрики с хоста: в `prometheus.yml` указан `host.docker.internal:8003`; при смене порта или запуске API в сети Docker поправьте target.

## Логин и JWT

1. Создайте аккаунт в таблице `account` (через репозиторий/тесты или SQL; пароль хранится как MD5-hex).
2. `POST /login` с телом `{"login":"...","password":"..."}` — в ответе cookie `access_token`.
3. Защищённые ручки: `/predict`, `/simple_predict`, `/async_predict`, `/moderation_result/{task_id}` — нужна эта cookie (или передайте тот же токен вручную; по умолчанию проверяется cookie).

## Запуск воркера Kafka

Отдельный процесс, каталог **`src`** должен быть в `PYTHONPATH` (скрипт сам добавляет его при прямом запуске файла).

```bash
cd src
python -m workers.moderation_worker
```
(из корня проекта `home_project`.)

Переменные: `DATABASE_URL`, `KAFKA_BOOTSTRAP_SERVERS` (для Docker по умолчанию у продюсера в приложении часто `localhost:9092`; из контейнера API — `redpanda:29092`). При `USE_MLFLOW=true` задайте `MLFLOW_TRACKING_URI` (на хосте: `http://localhost:5000`).

Несколько процессов воркера с одним `group_id` разделяют партиции.

## Тесты

Юнит-тесты (без PostgreSQL/Redis/Kafka):

```bash
cd home_project
export TESTING=1
export JWT_SECRET=test-jwt-secret-at-least-32-characters
pytest -m "not integration"
```

Интеграционные (нужны поднятые сервисы или будет skip на недоступных):

```bash
export TEST_DATABASE_URL=postgresql://moderation_user:moderation_password@localhost:5432/moderation_db
export TEST_REDIS_URL=redis://127.0.0.1:6379/15
pytest -m integration
```

Все тесты:

```bash
pytest
```

## Основные эндпоинты

- `POST /login` — авторизация, cookie JWT  
- `POST /predict` — предсказание по телу запроса  
- `POST /simple_predict?item_id=` — данные из БД + предсказание  
- `POST /async_predict?item_id=` — задача в Kafka  
- `GET /moderation_result/{task_id}` — статус/результат модерации  
- `POST /close?item_id=` — удаление объявления, модерации и инвалидация Redis  
- `GET /metrics` — Prometheus  

## Скринкаст для сдачи

Коротко покажите: вызов API (логин + predict/simple_predict), сообщение в топике модерации, обработку воркером, графики/Targets в Prometheus (и при необходимости Grafana).
