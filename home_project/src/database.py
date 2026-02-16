import asyncpg
import logging
import os

logger = logging.getLogger(__name__)

pool = None
current_db_url = None


def get_database_url():
    return os.getenv(
        "DATABASE_URL",
        "postgresql://moderation_user:moderation_password@localhost:5432/moderation_db"
    )


async def get_db_pool():
    global pool, current_db_url
    db_url = get_database_url()
    
    if pool is None or current_db_url != db_url:
        if pool:
            await pool.close()
        
        pool = await asyncpg.create_pool(
            db_url,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        current_db_url = db_url
        logger.info("Подключение к базе данных установлено")
    return pool


async def close_db_pool():
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("Подключение к базе данных закрыто")
