from src.db.db_models import PlayerCard
from src.enums import BonusCardEventType


def map_bonus_card_to_event_type(card: PlayerCard) -> BonusCardEventType:
    match card.status:
        case "active":
            if card.stolen_from_player is not None:
                return BonusCardEventType.LOOTED
            return BonusCardEventType.RECEIVED
        case "used":
            return BonusCardEventType.USED
        case "lost":
            return BonusCardEventType.LOST
        case "stolen":
            return BonusCardEventType.STOLEN

    raise ValueError(f"Unknown card status: {card.status}")


def get_closest_prison_sector(current_sector: int) -> int:
    prison_sectors = [11, 31]
    closest_sector = min(prison_sectors, key=lambda x: abs(x - current_sector))
    return closest_sector
