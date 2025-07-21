# database.py
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    async_sessionmaker,  # pyright: ignore[reportAttributeAccessIssue]
    create_async_engine,
)

from src.db.db_models import (
    DbBase,
)

from src.config import DATABASE_URL

is_sqlite = DATABASE_URL.startswith("sqlite")


# print(f"Using database URL: {DATABASE_URL}")


# def make_statement_name():
#     """Generate a unique statement name for asyncpg."""
#     return f"__asyncpg_{uuid4()}__"


if is_sqlite:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        # connect_args={
        #     "statement_cache_size": 0,
        #     "prepared_statement_cache_size": 0,
        #     "ssl": "require",
        #     "prepared_statement_name_func": make_statement_name,
        # },
    )
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session():
    async with SessionLocal() as session:
        yield session


async def init_db_async():
    async with engine.begin() as conn:
        await conn.run_sync(DbBase.metadata.create_all)


# async def test_connection():
#     print(f"Using database URL: {DATABASE_URL}")
#     print(f"Testing database connection: {TEST_DB_URL}")
#     conn = await asyncpg.connect(TEST_DB_URL, statement_cache_size=0)
#     version = await conn.fetchval("SELECT version();")
#     print(f"Connected! PostgreSQL version: {version}")
#     await conn.close()


if __name__ == "__main__":
    # asyncio.run(test_connection())
    asyncio.run(init_db_async())
    print("Database initialized successfully.")
