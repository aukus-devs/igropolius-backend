from src.api_models import BonusCardEvent
from src.db.db_models import PlayerCard
from src.enums import BonusCardEventType, BonusCardStatus, BonusCardType


def get_closest_prison_sector(current_sector: int) -> int:
    prison_sectors = [11, 31]
    closest_sector = min(prison_sectors, key=lambda x: abs(x - current_sector))
    return closest_sector


def get_bonus_cards_received_events(cards: list[PlayerCard]) -> list[BonusCardEvent]:
    events = []
    for card in cards:
        if card.status == BonusCardStatus.ACTIVE.value:
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
                timestamp=card.used_at,
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
                sector_id=card.sector_id,
                timestamp=card.stolen_at,
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
                timestamp=card.lost_at,
            )
            events.append(event)
    return events


def get_bonus_cards_looted_events(cards: list[PlayerCard]) -> list[BonusCardEvent]:
    events = []
    for card in cards:
        if (
            card.status == BonusCardStatus.ACTIVE.value
            and card.stolen_from_player is not None
        ):
            event = BonusCardEvent(
                event_type="bonus-card",
                subtype=BonusCardEventType.STOLEN_BY_ME,
                bonus_type=BonusCardType(card.card_type),
                sector_id=card.sector_id,
                timestamp=card.stolen_at,
                stolen_from_player=card.stolen_from_player,
            )
            events.append(event)
    return events
