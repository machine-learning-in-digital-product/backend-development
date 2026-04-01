import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from services.auth_service import AuthService


def test_create_and_decode_roundtrip():
    svc = AuthService(secret="unit-test-jwt-secret-32-bytes-ok")
    token = svc.create_access_token(42, "user42")
    data = svc.decode_token(token)
    assert data["sub"] == "42"
    assert data["login"] == "user42"


def test_decode_rejects_wrong_secret():
    svc_a = AuthService(secret="jwt-test-secret-number-one-32bytes")
    svc_b = AuthService(secret="jwt-test-secret-number-two-32bytes")
    token = svc_a.create_access_token(1, "x")
    with pytest.raises(jwt.PyJWTError):
        svc_b.decode_token(token)


def test_decode_rejects_expired():
    sec = "expired-token-test-secret-32bytes!"
    svc = AuthService(secret=sec)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "1",
        "login": "u",
        "exp": now - timedelta(seconds=1),
        "iat": now - timedelta(hours=1),
    }
    token = jwt.encode(payload, sec, algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        svc.decode_token(token)
