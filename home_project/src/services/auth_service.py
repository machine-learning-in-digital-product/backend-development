import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt


class AuthService:
    def __init__(self, secret: Optional[str] = None, algorithm: str = "HS256"):
        self._secret = secret or os.getenv(
            "JWT_SECRET",
            "dev-jwt-secret-placeholder-min-32-chars-long",
        )
        self._algorithm = algorithm

    def create_access_token(
        self, account_id: int, login: str, expires_hours: int = 24
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(account_id),
            "login": login,
            "exp": now + timedelta(hours=expires_hours),
            "iat": now,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_token(self, token: str) -> dict:
        return jwt.decode(token, self._secret, algorithms=[self._algorithm])


auth_service = AuthService()
