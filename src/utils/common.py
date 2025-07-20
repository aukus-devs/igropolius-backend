from src.db.db_models import PlayerCard
from src.enums import BonusCardEventType, BonusCardStatus


def map_bonus_card_to_event_type(card: PlayerCard) -> BonusCardEventType:
    match card.status:
        case BonusCardStatus.ACTIVE.value:
            if card.stolen_from_player is not None:
                return BonusCardEventType.STOLEN_BY_ME
            return BonusCardEventType.RECEIVED
        case BonusCardStatus.USED.value:
            return BonusCardEventType.USED
        case BonusCardStatus.DROPPED.value:
            return BonusCardEventType.DROPPED
        case BonusCardStatus.STOLEN.value:
            return BonusCardEventType.STOLEN_FROM_ME
        case _:
            raise ValueError(f"Unknown card status: {card.status}")


def get_closest_prison_sector(current_sector: int) -> int:
    prison_sectors = [11, 31]
    closest_sector = min(prison_sectors, key=lambda x: abs(x - current_sector))
    return closest_sector
