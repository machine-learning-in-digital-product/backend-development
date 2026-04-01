import asyncpg
from typing import Optional
from datetime import datetime
from database import get_db_pool


class ModerationResultsRepository:
    async def create_task(self, item_id: int) -> dict:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO moderation_results (item_id, status)
                VALUES ($1, 'pending')
                RETURNING id, item_id, status, is_violation, probability, error_message, created_at, processed_at
                """,
                item_id
            )
            return dict(row) if row else None
    
    async def get_task_by_id(self, task_id: int) -> Optional[dict]:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, item_id, status, is_violation, probability, error_message, created_at, processed_at
                FROM moderation_results
                WHERE id = $1
                """,
                task_id
            )
            return dict(row) if row else None
    
    async def get_tasks_by_item_id(self, item_id: int) -> list:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, item_id, status, is_violation, probability, error_message, created_at, processed_at
                FROM moderation_results
                WHERE item_id = $1
                ORDER BY created_at DESC
                """,
                item_id
            )
            return [dict(row) for row in rows]
    
    async def update_task_completed(self, task_id: int, is_violation: bool, probability: float) -> None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE moderation_results
                SET status = 'completed',
                    is_violation = $2,
                    probability = $3,
                    processed_at = CURRENT_TIMESTAMP
                WHERE id = $1
                """,
                task_id, is_violation, probability
            )
    
    async def update_task_failed(self, task_id: int, error_message: str) -> None:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE moderation_results
                SET status = 'failed',
                    error_message = $2,
                    processed_at = CURRENT_TIMESTAMP
                WHERE id = $1
                """,
                task_id, error_message
            )
