from sqlalchemy import distinct, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.api_models import BonusCardEvent
from src.consts import SECTORS_COLORS_GROUPS
from src.db.db_models import PlayerCard, PlayerGame, User
from src.enums import (
    BonusCardEventType,
    BonusCardStatus,
    BonusCardType,
    GameCompletionType,
    InstantCardType,
)


def get_closest_prison_sector(current_sector: int) -> int:
    prison_sectors = [11, 31]
    closest_sector = min(prison_sectors, key=lambda x: abs(x - current_sector))
    return closest_sector


def get_bonus_cards_received_events(cards: list[PlayerCard]) -> list[BonusCardEvent]:
    events = []
    for card in cards:
        if card.stolen_from_player is None and not is_instant_card(card.card_type):
            event = BonusCardEvent(
                event_type="bonus-card",
                subtype=BonusCardEventType.RECEIVED,
                bonus_type=BonusCardType(card.card_type),
                sector_id=card.received_on_sector,
                timestamp=card.created_at,
            )
            events.append(event)
    return events


def get_bonus_cards_used_events(cards: list[PlayerCard]) -> list[BonusCardEvent]:
    events = []
    for card in cards:
        if card.status == BonusCardStatus.USED.value:
            event = BonusCardEvent(
                event_type="bonus-card",
                subtype=BonusCardEventType.USED,
                bonus_type=BonusCardType(card.card_type),
                sector_id=card.used_on_sector,
                timestamp=card.used_at or card.updated_at,
            )
            events.append(event)
    return events


def get_bonus_cards_stolen_events(cards: list[PlayerCard]) -> list[BonusCardEvent]:
    events = []
    for card in cards:
        if card.status == BonusCardStatus.STOLEN.value:
            event = BonusCardEvent(
                event_type="bonus-card",
                subtype=BonusCardEventType.STOLEN_FROM_ME,
                bonus_type=BonusCardType(card.card_type),
                sector_id=card.lost_on_sector,
                timestamp=card.stolen_at or card.updated_at,
                stolen_by=card.stolen_by,
            )
            events.append(event)
    return events


def get_bonus_cards_dropped_events(cards: list[PlayerCard]) -> list[BonusCardEvent]:
    events = []
    for card in cards:
        if card.status == BonusCardStatus.DROPPED.value:
            event = BonusCardEvent(
                event_type="bonus-card",
                subtype=BonusCardEventType.DROPPED,
                bonus_type=BonusCardType(card.card_type),
                sector_id=card.lost_on_sector,
                timestamp=card.lost_at or card.updated_at,
            )
            events.append(event)
    return events


def get_bonus_cards_looted_events(cards: list[PlayerCard]) -> list[BonusCardEvent]:
    events = []
    for card in cards:
        if card.stolen_from_player is not None:
            event = BonusCardEvent(
                event_type="bonus-card",
                subtype=BonusCardEventType.STOLEN_BY_ME,
                bonus_type=BonusCardType(card.card_type),
                sector_id=card.received_on_sector,
                timestamp=card.created_at,
                stolen_from_player=card.stolen_from_player,
            )
            events.append(event)
    return events


def find_sector_group(sector_id: int) -> list[int] | None:
    for group in SECTORS_COLORS_GROUPS:
        if sector_id in group:
            return group
    return None


async def player_owns_sectors_group(
    db: AsyncSession, player: User, sectors_group: list[int]
) -> bool:
    query = select(func.count(distinct(PlayerGame.sector_id))).where(
        PlayerGame.player_id == player.id,
        PlayerGame.sector_id.in_(sectors_group),
        PlayerGame.type == GameCompletionType.COMPLETED.value,
    )
    result = await db.execute(query)
    sectors_owned = result.scalar()
    return sectors_owned == len(sectors_group)


InstantCardsValues = {i.value for i in InstantCardType}


def is_instant_card(value: str) -> bool:
    return value in InstantCardsValues


def is_first_day() -> bool:
    return False
