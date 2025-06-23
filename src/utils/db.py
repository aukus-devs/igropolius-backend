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


async def log_error_to_db(
    session: AsyncSession,
    error: Exception,
    function_name: str,
    player_id: int | None = None,
    context: str | None = None,
):
    from src.db_models import ErrorLog

    error_log = ErrorLog(
        player_id=player_id,
        error_type=type(error).__name__,
        error_message=str(error),
        function_name=function_name,
        context=context,
    )

    session.add(error_log)
    await safe_commit(session)
