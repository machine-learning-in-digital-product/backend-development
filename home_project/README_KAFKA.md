# Асинхронная обработка модерации через Kafka

## Описание

Сервис модерации объявлений с асинхронной обработкой через Kafka. Объявления отправляются в очередь Kafka и обрабатываются фоновыми воркерами.

## Архитектура

- **FastAPI** - API сервер для приема запросов
- **Redpanda** - Kafka-совместимый брокер сообщений
- **PostgreSQL** - база данных для хранения результатов модерации
- **Воркеры** - фоновые процессы для обработки сообщений из Kafka

## Установка и запуск

### 1. Запуск инфраструктуры

```bash
docker-compose up -d
```

Это запустит:
- PostgreSQL на порту 5432
- Redpanda (Kafka) на порту 9092
- Redpanda Console на http://localhost:8080

### 2. Применение миграций

```bash
python run_migrations.py
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Запуск FastAPI сервера

```bash
python -m src.main
```

Сервер будет доступен на http://localhost:8003

### 5. Запуск воркера

В отдельном терминале:

```bash
python -m src.workers.moderation_worker
```

Можно запустить несколько воркеров для параллельной обработки.

## API Endpoints

### POST /async_predict

Создает задачу на асинхронную модерацию объявления.

**Параметры:**
- `item_id` (int) - ID объявления

**Пример запроса:**
```bash
curl -X POST "http://localhost:8003/async_predict?item_id=123"
```

**Пример ответа:**
```json
{
  "task_id": 1,
  "status": "pending",
  "message": "Moderation request accepted"
}
```

### GET /moderation_result/{task_id}

Получает статус и результат модерации по ID задачи.

**Пример запроса:**
```bash
curl "http://localhost:8003/moderation_result/1"
```

**Пример ответа (pending):**
```json
{
  "task_id": 1,
  "status": "pending",
  "is_violation": null,
  "probability": null
}
```

**Пример ответа (completed):**
```json
{
  "task_id": 1,
  "status": "completed",
  "is_violation": false,
  "probability": 0.15
}
```

**Пример ответа (failed):**
```json
{
  "task_id": 1,
  "status": "failed",
  "is_violation": null,
  "probability": null,
  "error_message": "Модель не загружена"
}
```

## Kafka Topics

- **moderation** - основной топик для запросов на модерацию
- **moderation_dlq** - Dead Letter Queue для сообщений с ошибками

## Просмотр сообщений в Kafka

Откройте Redpanda Console: http://localhost:8080

В консоли можно:
- Просматривать сообщения в топиках
- Мониторить consumer groups
- Анализировать ошибки в DLQ

## Переменные окружения

- `KAFKA_BOOTSTRAP_SERVERS` - адрес Kafka брокера (по умолчанию: `localhost:9092`)
- `DATABASE_URL` - строка подключения к PostgreSQL
- `USE_MLFLOW` - использовать MLflow для загрузки модели (`true`/`false`)
- `REGISTER_MODEL` - зарегистрировать модель в MLflow при запуске (`true`/`false`)

## Тестирование

```bash
pytest tests/test_async_predict.py -v
```
## Dead Letter Queue (DLQ)

При ошибке обработки сообщения:
1. Задача в БД помечается как `failed` с сообщением об ошибке
2. Сообщение отправляется в топик `moderation_dlq` для последующего анализа

Формат сообщения в DLQ:
```json
{
  "original_message": {
    "item_id": 123,
    "timestamp": "2025-01-28T12:00:00"
  },
  "error": "Объявление не найдено",
  "timestamp": "2025-01-28T12:00:05",
  "retry_count": 1
}
```
