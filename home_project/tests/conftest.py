import sys
from pathlib import Path
import os

os.environ["TESTING"] = "1"

import pytest
import asyncpg
import httpx
from asgi_lifespan import LifespanManager

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://moderation_user:moderation_password@localhost:5432/moderation_db",
)


@pytest.fixture(scope="function")
async def db_pool():
    """Очистка таблиц в PostgreSQL для интеграционных тестов репозиториев и БД."""
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    from database import close_db_pool, pool

    if pool:
        await close_db_pool()

    conn = await asyncpg.connect(TEST_DATABASE_URL)
    try:
        migration_004 = project_root / "migrations" / "004_items_is_closed.sql"
        if migration_004.exists():
            await conn.execute(migration_004.read_text())
        await conn.execute("TRUNCATE TABLE moderation_results CASCADE")
        await conn.execute("TRUNCATE TABLE items CASCADE")
        await conn.execute("TRUNCATE TABLE users CASCADE")
    finally:
        await conn.close()

    yield

    from database import close_db_pool as _close, pool as _pool

    if _pool:
        await _close()

    if original_db_url:
        os.environ["DATABASE_URL"] = original_db_url
    elif "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]


@pytest.fixture
async def client():
    """HTTP-клиент приложения; Redis по умолчанию выключен (без REDIS_URL)."""
    prev_redis = os.environ.pop("REDIS_URL", None)
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    if prev_redis is not None:
        os.environ["REDIS_URL"] = prev_redis


@pytest.fixture
async def integration_client(integration_redis):
    """AsyncClient с подключённым Redis (интеграция API + кэш)."""
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def integration_redis():
    """Включает Redis для интеграционных тестов кэша (отдельная БД Redis 15)."""
    from clients.redis_client import close_redis, get_redis

    url = os.getenv("TEST_REDIS_URL", "redis://127.0.0.1:6379/15")
    prev = os.environ.get("REDIS_URL")
    await close_redis()
    os.environ["REDIS_URL"] = url
    try:
        r = await get_redis()
        await r.ping()
        await r.flushdb()
    except OSError:
        await close_redis()
        if prev is None:
            os.environ.pop("REDIS_URL", None)
        else:
            os.environ["REDIS_URL"] = prev
        pytest.skip("Redis недоступен")
    except Exception:
        await close_redis()
        if prev is None:
            os.environ.pop("REDIS_URL", None)
        else:
            os.environ["REDIS_URL"] = prev
        pytest.skip("Не удалось подключиться к Redis")

    yield url

    await close_redis()
    if prev is None:
        os.environ.pop("REDIS_URL", None)
    else:
        os.environ["REDIS_URL"] = prev
