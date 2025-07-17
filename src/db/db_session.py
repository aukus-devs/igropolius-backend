# database.py
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.ext.asyncio import (  # pyright: ignore[reportAttributeAccessIssue]
    async_sessionmaker,
    create_async_engine,
)

from src.config import DATABASE_URL
from src.db.db_models import (
    DbBase,
)

is_sqlite = DATABASE_URL.startswith("sqlite")


# print(f"Using database URL: {DATABASE_URL}")


# def make_statement_name():
#     """Generate a unique statement name for asyncpg."""
#     return f"__asyncpg_{uuid4()}__"


def create_engine():
    if is_sqlite:
        return create_async_engine(
            DATABASE_URL,
            echo=False,
        )
    else:
        return create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            connect_args={
                "autocommit": False,
                "charset": "utf8mb4",
                "sql_mode": "STRICT_TRANS_TABLES",
                "init_command": "SET SESSION wait_timeout=28800, interactive_timeout=28800, net_read_timeout=60, net_write_timeout=60",
            },
        )


engine = create_engine()


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    if not is_sqlite:
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        except Exception:
            connection_proxy._pool.dispose()
            raise


SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db():
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            async with SessionLocal() as session:
                try:
                    yield session
                    await session.commit()
                except (OperationalError, DisconnectionError) as e:
                    await session.rollback()
                    if "Lost connection" in str(
                        e
                    ) or "MySQL server has gone away" in str(e):
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(0.1 * retry_count)
                            continue
                    raise
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
                break
        except (OperationalError, DisconnectionError):
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(0.1 * retry_count)
                continue
            raise


@asynccontextmanager
async def get_session():
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            async with SessionLocal() as session:
                try:
                    yield session
                except (OperationalError, DisconnectionError) as e:
                    if "Lost connection" in str(
                        e
                    ) or "MySQL server has gone away" in str(e):
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(0.1 * retry_count)
                            continue
                    raise
                break
        except (OperationalError, DisconnectionError):
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(0.1 * retry_count)
                continue
            raise


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
