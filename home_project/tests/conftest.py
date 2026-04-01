import sys
from pathlib import Path
import os

os.environ["TESTING"] = "1"
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-at-least-32-characters")

import pytest
import asyncpg
import httpx
from asgi_lifespan import LifespanManager

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from main import app
from dependencies.auth import get_current_account
from models.account import Account

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://moderation_user:moderation_password@localhost:5432/moderation_db",
)


@pytest.fixture(scope="function")
async def db_pool():
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    from database import close_db_pool, pool

    if pool:
        await close_db_pool()

    conn = await asyncpg.connect(TEST_DATABASE_URL)
    try:
        for name in ("004_items_is_closed.sql", "005_account.sql"):
            path = project_root / "migrations" / name
            if path.exists():
                await conn.execute(path.read_text())
        await conn.execute("TRUNCATE TABLE moderation_results CASCADE")
        await conn.execute("TRUNCATE TABLE account CASCADE")
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


@pytest.fixture(autouse=True)
def _auth_dependency_override():
    async def _fake_account() -> Account:
        return Account(id=1, login="testuser", is_blocked=False)

    app.dependency_overrides[get_current_account] = _fake_account
    yield
    app.dependency_overrides.pop(get_current_account, None)


@pytest.fixture
async def client():
    prev_redis = os.environ.pop("REDIS_URL", None)
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    if prev_redis is not None:
        os.environ["REDIS_URL"] = prev_redis


@pytest.fixture
async def integration_client(integration_redis):
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def integration_redis():
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
