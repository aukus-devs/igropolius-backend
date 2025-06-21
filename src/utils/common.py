from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.db_models import PlayerCard
from src.enums import BonusCardEventType


def utc_now_ts():
    utc_now = datetime.now(timezone.utc)
    return int(utc_now.timestamp())


async def safe_commit(session: AsyncSession):
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise


def map_bonus_card_to_event_type(card: PlayerCard) -> BonusCardEventType:
    if card.status == "active":
        if card.stolen_from_player is not None:
            return BonusCardEventType.LOOTED
        return BonusCardEventType.RECEIVED
    if card.status == "used":
        return BonusCardEventType.USED
    if card.status == "lost":
        return BonusCardEventType.LOST
    if card.status == "stolen":
        return BonusCardEventType.STOLEN

    raise ValueError(f"Unknown card status: {card.status}")
