# database.py
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.db_models import DbBase
from .config import DATABASE_URL, IS_LOCAL

is_sqlite = DATABASE_URL.startswith("sqlite")


engine = create_async_engine(DATABASE_URL, echo=IS_LOCAL)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db_async():
    async with engine.begin() as conn:
        await conn.run_sync(DbBase.metadata.create_all)


@asynccontextmanager
async def get_session():
    async with SessionLocal() as session:
        yield session


if __name__ == "__main__":
    import asyncio

    asyncio.run(init_db_async())
    print("Database initialized successfully.")
