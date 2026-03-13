import asyncpg

from app.config import settings

pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    return pool


async def init_db() -> None:
    global pool
    pool = await asyncpg.create_pool(
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db,
        host=settings.postgres_host,
        port=settings.postgres_port,
        min_size=2,
        max_size=10,
    )


async def close_db() -> None:
    global pool
    if pool:
        await pool.close()
        pool = None
