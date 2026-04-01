-- Демо-данные для ручных запросов (логин demo / пароль demo123, MD5 пароля в БД).
-- Выполнить: psql "$DATABASE_URL" -f docs/seed-demo.sql

INSERT INTO account (login, password, is_blocked)
VALUES ('demo', '62cc2d8b4bf2d8728120d052163a77df', false)
ON CONFLICT (login) DO UPDATE SET
    password = EXCLUDED.password,
    is_blocked = false;

INSERT INTO users (seller_id, is_verified_seller)
VALUES (100, true)
ON CONFLICT (seller_id) DO UPDATE SET is_verified_seller = EXCLUDED.is_verified_seller;

INSERT INTO items (item_id, seller_id, name, description, category, images_qty, is_closed)
VALUES (9001, 100, 'Демо товар', 'Описание для проверки модерации и simple_predict', 2, 3, false)
ON CONFLICT (item_id) DO UPDATE SET
    seller_id = EXCLUDED.seller_id,
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    images_qty = EXCLUDED.images_qty,
    is_closed = false;
