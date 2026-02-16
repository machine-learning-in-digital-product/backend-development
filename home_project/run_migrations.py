import os
import subprocess
import sys
import asyncio
import asyncpg
from pathlib import Path

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://moderation_user:moderation_password@localhost:5432/moderation_db"
)


def run_with_pgmigrate():
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    
    try:
        result = subprocess.run(
            [
                "pgmigrate",
                "migrate",
                "--migrations-dir", migrations_dir,
                "--connection-string", DATABASE_URL
            ],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
    except FileNotFoundError:
        return False


async def run_with_asyncpg():
    migrations_dir = Path(__file__).parent / "migrations"
    migration_file = migrations_dir / "001_initial_schema.sql"
    
    if not migration_file.exists():
        print(f"Файл миграции не найден: {migration_file}")
        return False
    
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        migration_sql = migration_file.read_text()
        await conn.execute(migration_sql)
        print("Миграция успешно применена!")
        return True
    except Exception as e:
        print(f"Ошибка при применении миграции: {e}")
        return False
    finally:
        await conn.close()


if __name__ == "__main__":
    if run_with_pgmigrate():
        sys.exit(0)
    
    print("pgmigrate не найден, используем asyncpg...")
    success = asyncio.run(run_with_asyncpg())
    sys.exit(0 if success else 1)
