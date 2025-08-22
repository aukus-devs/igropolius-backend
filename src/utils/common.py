from typing import cast
from typing_extensions import TypedDict
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession


from src.api_models import BonusCardEvent
from src.consts import (
    ACTIVE_CARD_TYPES,
    FIRST_DAY_SECONDS,
    INSTANT_CARD_TYPES,
    SECTOR_SCORE_MULTIPLIERS,
    SECTORS_COLORS_GROUPS,
)
from src.db.db_models import EventSettings, PlayerCard, PlayerGame, PlayerMove, User
from src.enums import (
    BonusCardEventType,
    BonusCardStatus,
    BonusCardType,
    EventSetting,
    GameCompletionType,
    PlayerMoveType,
    Role,
)
from src.utils.db import utc_now_ts


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
                instant_card_score_multiplier=card.instant_card_score_multiplier,
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


def is_instant_card(value: str) -> bool:
    return value in INSTANT_CARD_TYPES


async def get_event_setting(db: AsyncSession, setting: EventSetting) -> str | None:
    query = select(EventSettings).where(EventSettings.key_name == setting.value)
    result = await db.execute(query)
    db_setting = result.scalar_one_or_none()
    if db_setting:
        return db_setting.value
    return None


async def is_first_day(db: AsyncSession) -> bool:
    setting = await get_event_setting(db, EventSetting.EVENT_START_TIME)
    if setting is None:
        return False
    start_time = int(setting)
    utc_now = utc_now_ts()
    return utc_now < start_time + FIRST_DAY_SECONDS


def get_sector_score_multiplier(sector_id: int) -> float:
    return SECTOR_SCORE_MULTIPLIERS.get(sector_id, 1)


async def get_prison_user(db: AsyncSession) -> User | None:
    prison_query = (
        select(User).where(User.role == Role.PRISON.value).where(User.is_active == 1)
    )
    prison = await db.execute(prison_query)
    prison_user = prison.scalars().first()
    return prison_user


async def get_last_card_usage(db: AsyncSession) -> list[tuple[int, str, int]]:
    # Construct the query
    query = (
        select(
            PlayerCard.player_id,
            PlayerCard.card_type,
            func.max(PlayerCard.used_at).label("last_used_at"),
        )
        .where(PlayerCard.card_type.in_(ACTIVE_CARD_TYPES))
        .where(PlayerCard.status == BonusCardStatus.USED.value)
        .where(PlayerCard.used_at.is_not(None))
        .group_by(PlayerCard.player_id, PlayerCard.card_type)
        .order_by(PlayerCard.player_id, PlayerCard.card_type)
    )

    result = await db.execute(query)
    last_cards = result.all()
    return cast(list[tuple[int, str, int]], last_cards)


async def get_last_moves(db: AsyncSession, limit: int) -> list[PlayerMove]:
    subquery = (
        select(
            PlayerMove,
            func.row_number()
            .over(partition_by=PlayerMove.player_id, order_by=PlayerMove.id.desc())
            .label("row_num"),
        )
        .select_from(PlayerMove)
        .where(
            PlayerMove.move_type.in_(
                [PlayerMoveType.DICE_ROLL.value, PlayerMoveType.DROP_TO_PRISON.value]
            )
        )
        .subquery()
    )
    query = (
        select(PlayerMove)
        .join(subquery, PlayerMove.id == subquery.c.id)
        .where(subquery.c.row_num <= limit)
    )

    # query = select(subquery).where(subquery.c.row_num <= limit)
    result = await db.execute(query)
    moves = result.scalars().all()
    return moves


class MoveWithAge(TypedDict):
    age: int
    move: PlayerMove


async def get_cards_used_in_last_moves(
    db: AsyncSession, moves: int
) -> dict[int, dict[str, MoveWithAge]]:
    last_moves = await get_last_moves(db, moves)
    cards_usage = await get_last_card_usage(db)

    moves_ordered = sorted(last_moves, key=lambda move: move.created_at, reverse=True)

    moves_by_player = {}
    for move in moves_ordered:
        if move.player_id not in moves_by_player:
            moves_by_player[move.player_id] = []
        moves_by_player[move.player_id].append(move)

    cards_used_per_player = {}
    for card_usage in cards_usage:
        player_id, card_type, last_used_at = card_usage
        if player_id not in cards_used_per_player:
            cards_used_per_player[player_id] = {}
        if card_type not in cards_used_per_player[player_id]:
            cards_used_per_player[player_id][card_type] = {}

        player_moves = moves_by_player.get(player_id, [])
        for idx, move in enumerate(player_moves):
            if move.created_at < last_used_at:
                cards_used_per_player[player_id][card_type] = {
                    "move_age": idx,
                    "move": move,
                }
                break

    return cards_used_per_player
