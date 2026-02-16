import asyncpg
from typing import Optional
from database import get_db_pool


class ItemRepository:
    async def create_item(
        self,
        item_id: int,
        seller_id: int,
        name: str,
        description: str,
        category: int,
        images_qty: int
    ) -> dict:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO items (item_id, seller_id, name, description, category, images_qty)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (item_id)
                DO UPDATE SET 
                    seller_id = $2,
                    name = $3,
                    description = $4,
                    category = $5,
                    images_qty = $6,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, item_id, seller_id, name, description, category, images_qty, created_at, updated_at
                """,
                item_id, seller_id, name, description, category, images_qty
            )
            return dict(row) if row else None
    
    async def get_item_by_item_id(self, item_id: int) -> Optional[dict]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    i.id, i.item_id, i.seller_id, i.name, i.description, 
                    i.category, i.images_qty, i.created_at, i.updated_at,
                    u.is_verified_seller
                FROM items i
                JOIN users u ON i.seller_id = u.seller_id
                WHERE i.item_id = $1
                """,
                item_id
            )
            return dict(row) if row else None
