import pytest

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from repositories.account import AccountRepository, password_digest

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("db_pool")]


@pytest.mark.asyncio
async def test_create_and_get_by_id():
    repo = AccountRepository()
    row = await repo.create("alice", "secret")
    assert row is not None
    assert row["login"] == "alice"
    assert row["is_blocked"] is False
    got = await repo.get_by_id(row["id"])
    assert got == row


@pytest.mark.asyncio
async def test_find_by_login_and_password():
    repo = AccountRepository()
    await repo.create("bob", "pwd123")
    found = await repo.find_by_login_and_password("bob", "pwd123")
    assert found is not None
    assert found["login"] == "bob"
    wrong = await repo.find_by_login_and_password("bob", "other")
    assert wrong is None


@pytest.mark.asyncio
async def test_password_stored_as_md5_digest():
    repo = AccountRepository()
    created = await repo.create("digest", "x")
    pool_module = __import__("database", fromlist=["get_db_pool"])
    pool = await pool_module.get_db_pool()
    async with pool.acquire() as conn:
        raw = await conn.fetchrow(
            "SELECT password FROM account WHERE id = $1",
            created["id"],
        )
    assert raw["password"] == password_digest("x")


@pytest.mark.asyncio
async def test_block_prevents_login():
    repo = AccountRepository()
    row = await repo.create("cindy", "p")
    assert await repo.block(row["id"]) is True
    blocked = await repo.find_by_login_and_password("cindy", "p")
    assert blocked is None
    got = await repo.get_by_id(row["id"])
    assert got["is_blocked"] is True


@pytest.mark.asyncio
async def test_delete():
    repo = AccountRepository()
    row = await repo.create("dan", "p")
    assert await repo.delete(row["id"]) is True
    assert await repo.get_by_id(row["id"]) is None
