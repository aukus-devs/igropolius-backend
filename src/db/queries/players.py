from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.db.db_models import PlayerCard, PlayerScoreChange, User
from src.enums import ScoreChangeType


async def get_players_by_score(
    db: AsyncSession, *, for_update: bool = False, limit: int | None = None
) -> list[User]:
    query = (
        select(User)
        .where(
            User.is_active == 1,
            User.total_score.isnot(None),
            User.sector_id.isnot(None),
        )
        .order_by(User.total_score.desc())
    )
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
    player_card: PlayerCard | None = None,
) -> PlayerScoreChange:
    if not db.in_transaction():
        raise ValueError("Database session must be in a transaction")

    if change_type == ScoreChangeType.INSTANT_CARD and not player_card:
        raise ValueError("Player card must be provided for INSTANT_CARD score change")

    if (
        player.sector_id is None
        or player.maps_completed is None
        or player.total_score is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player data is not set",
        )

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
        bonus_card=player_card.card_type if player_card else None,
        bonus_card_owner=player_card.player_id if player_card else None,
        player_card_id=player_card.id if player_card else None,
    )
    db.add(score_change)
    player.total_score = after
    return score_change
