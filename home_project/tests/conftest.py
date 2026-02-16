import sys
from pathlib import Path
import pytest
import asyncio
from fastapi.testclient import TestClient
import os

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://moderation_user:moderation_password@localhost:5432/moderation_db"
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def db_pool():
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    
    from database import get_db_pool, close_db_pool, pool
    
    if pool:
        await close_db_pool()
    
    pool_instance = await get_db_pool()
    
    import asyncpg
    async with pool_instance.acquire() as conn:
        await conn.execute("TRUNCATE TABLE items CASCADE")
        await conn.execute("TRUNCATE TABLE users CASCADE")
    
    yield pool_instance
    
    await close_db_pool()
    
    if original_db_url:
        os.environ["DATABASE_URL"] = original_db_url
    elif "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]


@pytest.fixture
def client():
    return TestClient(app)
