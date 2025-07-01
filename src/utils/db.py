from datetime import datetime, timezone

from sqlalchemy import delete, update
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
    from src.db.db_models import ErrorLog

    error_log = ErrorLog(
        player_id=player_id,
        error_type=type(error).__name__,
        error_message=str(error),
        function_name=function_name,
        context=context,
    )

    session.add(error_log)
    await safe_commit(session)


async def reset_database(db: AsyncSession):
    from src.db.db_models import (
        DiceRoll,
        PlayerCard,
        PlayerGame,
        PlayerMove,
        PlayerScoreChange,
        User,
    )
    from src.enums import PlayerTurnState

    reset_players_query = update(User).values(
        {
            "sector_id": 1,
            "total_score": 0.0,
            "turn_state": PlayerTurnState.ROLLING_DICE.value,
            "maps_completed": 0,
        }
    )
    await db.execute(reset_players_query)

    print("resetting")

    delete_cards_query = delete(PlayerCard)
    await db.execute(delete_cards_query)

    delete_games_query = delete(PlayerGame)
    await db.execute(delete_games_query)

    delete_score_changes = delete(PlayerScoreChange)
    await db.execute(delete_score_changes)

    delete_moves = delete(PlayerMove)
    await db.execute(delete_moves)

    delete_dice_rolls = delete(DiceRoll)
    await db.execute(delete_dice_rolls)
