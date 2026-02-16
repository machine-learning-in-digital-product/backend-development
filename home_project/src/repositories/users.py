import asyncpg
from typing import Optional
from database import get_db_pool


class UserRepository:
    async def create_user(self, seller_id: int, is_verified_seller: bool) -> dict:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (seller_id, is_verified_seller)
                VALUES ($1, $2)
                ON CONFLICT (seller_id) 
                DO UPDATE SET is_verified_seller = $2, updated_at = CURRENT_TIMESTAMP
                RETURNING id, seller_id, is_verified_seller, created_at, updated_at
                """,
                seller_id, is_verified_seller
            )
            return dict(row) if row else None
    
    async def get_user_by_seller_id(self, seller_id: int) -> Optional[dict]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, seller_id, is_verified_seller, created_at, updated_at FROM users WHERE seller_id = $1",
                seller_id
            )
            return dict(row) if row else None
