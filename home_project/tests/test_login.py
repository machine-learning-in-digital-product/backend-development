from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status

import routers.login as login_mod


@pytest.mark.asyncio
@patch.object(login_mod.account_repository, "find_by_login_and_password", new_callable=AsyncMock)
async def test_login_success_sets_cookie(mock_find, client):
    mock_find.return_value = {"id": 10, "login": "u1", "is_blocked": False}
    response = await client.post(
        "/login", json={"login": "u1", "password": "any"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.cookies.get("access_token")


@pytest.mark.asyncio
@patch.object(login_mod.account_repository, "find_by_login_and_password", new_callable=AsyncMock)
async def test_login_invalid_credentials(mock_find, client):
    mock_find.return_value = None
    response = await client.post(
        "/login", json={"login": "u1", "password": "wrong"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
