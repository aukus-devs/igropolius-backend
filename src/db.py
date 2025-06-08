# database.py
from contextlib import asynccontextmanager
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.db_models import DbBase
from .config import DATABASE_URL, IS_LOCAL
import asyncio
import asyncpg

is_sqlite = DATABASE_URL.startswith("sqlite")


engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"statement_cache_size": 0},
)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def get_session():
    async with SessionLocal() as session:
        yield session


async def init_db_async():
    async with engine.begin() as conn:
        await conn.run_sync(DbBase.metadata.create_all)


async def test_connection():
    pure_url = str(make_url(DATABASE_URL).set(drivername="postgresql"))
    print(f"Using database URL: {DATABASE_URL}")
    print(f"Testing database connection: {pure_url}")
    conn = await asyncpg.connect(pure_url, statement_cache_size=0)
    version = await conn.fetchval("SELECT version();")
    print(f"Connected! PostgreSQL version: {version}")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(test_connection())
    asyncio.run(init_db_async())
    print("Database initialized successfully.")
