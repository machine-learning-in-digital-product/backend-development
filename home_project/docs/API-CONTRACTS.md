# HTTP API: контракты и примеры

Базовый URL в примерах: `http://127.0.0.1:8003`.  
Авторизация защищённых методов: cookie **`access_token`** (HttpOnly), выдаётся после **`POST /login`**.

---

## Общие коды ответов

| Код | Когда |
|-----|--------|
| 200 | Успех (GET/POST с телом ответа) |
| 202 | Принят async-запрос (`/async_predict`) |
| 401 | Нет/битый JWT или заблокирован аккаунт |
| 404 | Сущность не найдена |
| 422 | Ошибка валидации query/body |
| 500 | Внутренняя ошибка / Kafka |
| 503 | Модель не загружена (`/predict`, `/simple_predict`) |

---

## 1. `GET /`

**Авторизация:** не требуется.

**Ответ 200**

```json
{ "message": "Hello World" }
```

```bash
curl -s http://127.0.0.1:8003/
```

---

## 2. `GET /metrics`

**Авторизация:** не требуется.

**Ответ 200:** `Content-Type: text/plain; version=0.0.4` — текст в формате Prometheus.

```bash
curl -s http://127.0.0.1:8003/metrics | head -20
```

---

## 3. `POST /login`

**Авторизация:** не требуется.

**Request body** (`application/json`)

| Поле | Тип | Ограничения |
|------|-----|-------------|
| login | string | min length 1 |
| password | string | min length 1 |

В БД пароль хранится как **MD5(hex)** от исходной строки; проверка — по хешу.

**Ответ 200**

```json
{ "status": "ok" }
```

В заголовке **`Set-Cookie`**: `access_token=<JWT>; HttpOnly; Path=/; Max-Age=604800; SameSite=lax`

**Ответ 401**

```json
{ "detail": "Неверный логин или пароль" }
```

**Контракт JWT (payload):** `sub` — id аккаунта (строка), `login`, `exp`, `iat`. Алгоритм **HS256**, секрет **`JWT_SECRET`**.

Демо-пользователь после `docs/seed-demo.sql`: **login `demo`**, **password `demo123`**.

```bash
curl -s -c cookies.txt -X POST http://127.0.0.1:8003/login \
  -H "Content-Type: application/json" \
  -d '{"login":"demo","password":"demo123"}'
```

---

## 4. `POST /predict`

**Авторизация:** обязательна — cookie `access_token`.

**Request body** (`application/json`)

| Поле | Тип | Ограничения |
|------|-----|-------------|
| seller_id | integer | > 0 |
| is_verified_seller | boolean | — |
| item_id | integer | > 0 |
| name | string | 1…500 символов |
| description | string | 0…5000 символов |
| category | integer | ≥ 0 |
| images_qty | integer | ≥ 0 |

**Ответ 200**

```json
{
  "is_violation": false,
  "probability": 0.42
}
```

**Ответ 401:** `{"detail": "Требуется авторизация"}` и т.п.

```bash
curl -s -b cookies.txt -X POST http://127.0.0.1:8003/predict \
  -H "Content-Type: application/json" \
  -d '{
    "seller_id": 100,
    "is_verified_seller": true,
    "item_id": 9001,
    "name": "Демо товар",
    "description": "Описание для проверки модерации и simple_predict",
    "category": 2,
    "images_qty": 3
  }'
```

---

## 5. `POST /simple_predict?item_id={int}`

**Авторизация:** обязательна.

**Query**

| Параметр | Тип | Ограничения |
|----------|-----|-------------|
| item_id | integer | > 0 |

Тело запроса пустое. Данные объявления читаются из БД по `item_id`.

**Ответ 200:** как у `/predict` — `PredictionResponse`.

**Ответ 404:** объявление не найдено.

После `seed-demo.sql` можно вызвать с **`item_id=9001`**.

```bash
curl -s -b cookies.txt -X POST \
  "http://127.0.0.1:8003/simple_predict?item_id=9001"
```

---

## 6. `POST /async_predict?item_id={int}`

**Авторизация:** обязательна.

**Query:** `item_id` > 0.

**Ответ 202**

```json
{
  "task_id": 1,
  "status": "pending",
  "message": "Moderation request accepted"
}
```

`task_id` — число из таблицы `moderation_results`.

```bash
curl -s -b cookies.txt -X POST \
  "http://127.0.0.1:8003/async_predict?item_id=9001"
```

---

## 7. `GET /moderation_result/{task_id}`

**Авторизация:** обязательна.

**Path:** `task_id` — положительный integer.

**Ответ 200**

```json
{
  "task_id": 1,
  "status": "pending",
  "is_violation": null,
  "probability": null,
  "error_message": null
}
```

Возможные `status`: `pending`, `completed`, `failed`. При `completed` заполняются `is_violation`, `probability`; при `failed` — `error_message`.

Подставьте `task_id` из ответа `/async_predict`.

```bash
TASK_ID=1
curl -s -b cookies.txt "http://127.0.0.1:8003/moderation_result/${TASK_ID}"
```

---

## 8. `POST /close?item_id={int}`

**Авторизация:** не требуется (в текущей реализации).

**Query:** `item_id` > 0.

Удаляет строку `items` (CASCADE по `moderation_results`), инвалидирует ключи Redis для этого объявления.

**Ответ 200**

```json
{ "item_id": 9001, "closed": true }
```

**Ответ 404:** объявления нет.

```bash
curl -s -X POST "http://127.0.0.1:8003/close?item_id=9001"
```

---

## Порядок «как всё проверить»

1. Поднять Postgres/Redis/Kafka и прогнать миграции + **`docs/seed-demo.sql`**.
2. Запустить API (`uvicorn` из `src` с `JWT_SECRET`, и т.д.).
3. **`POST /login`** с `demo` / `demo123`, сохранить cookie (`cookies.txt`).
4. **`POST /predict`**, **`/simple_predict?item_id=9001`**, **`/async_predict`**, **`/moderation_result/{id}`** с `-b cookies.txt`.
5. При необходимости **`POST /close`**.

Готовый сценарий shell: **`scripts/demo-api.sh`** (после логина и seed).
