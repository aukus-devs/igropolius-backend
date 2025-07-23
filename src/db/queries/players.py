from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.db_models import PlayerScoreChange, User
from src.enums import ScoreChangeType


async def get_players_by_score(
    db: AsyncSession, *, for_update: bool = False, limit: int | None = None
) -> list[User]:
    query = select(User).where(User.is_active == True).order_by(User.total_score.desc())
    if limit is not None:
        query = query.limit(limit)
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    players = result.scalars().all()
    return players


async def change_player_score(
    db: AsyncSession,
    player: User,
    score_change: float,
    change_type: ScoreChangeType,
    description: str,
    income_from_player: User | None = None,
) -> User:
    if not db.in_transaction():
        raise ValueError("Database session must be in a transaction")

    sector_id = player.sector_id
    income_from_player_id = None
    if income_from_player:
        sector_id = income_from_player.sector_id
        income_from_player_id = income_from_player.id

    score_change = round(score_change, 2)
    before = player.total_score
    after = round(before + score_change, 2)
    score_change = PlayerScoreChange(
        player_id=player.id,
        score_change=score_change,
        score_before=before,
        score_after=after,
        change_type=change_type.value,
        description=description,
        sector_id=sector_id,
        income_from_player=income_from_player_id,
    )
    db.add(score_change)
    player.total_score = after
    return player
