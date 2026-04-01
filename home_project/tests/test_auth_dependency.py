from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dependencies.auth import JWT_COOKIE_NAME, get_current_account
from models.account import Account
from services.auth_service import AuthService


@pytest.mark.asyncio
async def test_missing_cookie_raises_401():
    request = MagicMock()
    request.cookies = {}
    repo = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_account(request, repo)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_raises_401(monkeypatch):
    request = MagicMock()
    request.cookies = {JWT_COOKIE_NAME: "not-a-jwt"}
    repo = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_account(request, repo)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_returns_account_when_token_and_db_ok(monkeypatch):
    secret = "dep-secret-key-at-least-32-bytes-long!"
    svc = AuthService(secret=secret)
    token = svc.create_access_token(7, "seventh")

    request = MagicMock()
    request.cookies = {JWT_COOKIE_NAME: token}
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(
        return_value={"id": 7, "login": "seventh", "is_blocked": False}
    )

    monkeypatch.setattr(
        "dependencies.auth.auth_service",
        AuthService(secret=secret),
    )

    acc = await get_current_account(request, repo)
    assert isinstance(acc, Account)
    assert acc.id == 7
    assert acc.login == "seventh"
    repo.get_by_id.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_blocked_account_raises_401(monkeypatch):
    secret = "blocked-test-secret-key-32chars!!"
    svc = AuthService(secret=secret)
    token = svc.create_access_token(2, "blocked")

    request = MagicMock()
    request.cookies = {JWT_COOKIE_NAME: token}
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(
        return_value={"id": 2, "login": "blocked", "is_blocked": True}
    )

    monkeypatch.setattr(
        "dependencies.auth.auth_service",
        AuthService(secret=secret),
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_account(request, repo)
    assert exc.value.status_code == 401
