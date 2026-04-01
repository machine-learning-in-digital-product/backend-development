import pytest
from fastapi import status

from dependencies.auth import get_current_account
from main import app


@pytest.mark.asyncio
async def test_predict_without_auth_returns_401(client):
    app.dependency_overrides.pop(get_current_account, None)
    try:
        response = await client.post(
            "/predict",
            json={
                "seller_id": 12345,
                "is_verified_seller": True,
                "item_id": 67890,
                "name": "Товар",
                "description": "Описание",
                "category": 1,
                "images_qty": 5,
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    finally:
        async def _fake():
            from models.account import Account

            return Account(id=1, login="testuser", is_blocked=False)

        app.dependency_overrides[get_current_account] = _fake
