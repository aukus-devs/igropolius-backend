from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession


def utc_now_ts():
    utc_now = datetime.now(timezone.utc)
    return int(utc_now.timestamp())


async def safe_commit(session: AsyncSession):
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
