import hashlib
from typing import Optional

from database import get_db_pool
from metrics import record_db_query


def password_digest(plain: str) -> str:
    return hashlib.md5(plain.encode("utf-8")).hexdigest()


class AccountRepository:
    async def create(self, login: str, password: str) -> dict:
        digest = password_digest(password)
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await record_db_query(
                "insert",
                conn.fetchrow(
                    """
                    INSERT INTO account (login, password)
                    VALUES ($1, $2)
                    RETURNING id, login, is_blocked
                    """,
                    login,
                    digest,
                ),
            )
            return dict(row) if row else None

    async def get_by_id(self, account_id: int) -> Optional[dict]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await record_db_query(
                "select",
                conn.fetchrow(
                    """
                    SELECT id, login, is_blocked
                    FROM account
                    WHERE id = $1
                    """,
                    account_id,
                ),
            )
            return dict(row) if row else None

    async def delete(self, account_id: int) -> bool:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rec = await record_db_query(
                "delete",
                conn.fetchrow(
                    "DELETE FROM account WHERE id = $1 RETURNING id",
                    account_id,
                ),
            )
            return rec is not None

    async def block(self, account_id: int) -> bool:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rec = await record_db_query(
                "update",
                conn.fetchrow(
                    """
                    UPDATE account
                    SET is_blocked = TRUE
                    WHERE id = $1
                    RETURNING id
                    """,
                    account_id,
                ),
            )
            return rec is not None

    async def find_by_login_and_password(
        self, login: str, password: str
    ) -> Optional[dict]:
        digest = password_digest(password)
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await record_db_query(
                "select",
                conn.fetchrow(
                    """
                    SELECT id, login, is_blocked
                    FROM account
                    WHERE login = $1 AND password = $2 AND is_blocked = FALSE
                    """,
                    login,
                    digest,
                ),
            )
            return dict(row) if row else None
