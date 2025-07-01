from sqlalchemy.ext.asyncio import AsyncSession

from src.db_models import Notification
from src.enums import NotificationEventType, NotificationType
from src.utils.db import safe_commit, utc_now_ts


async def create_notification(
    db: AsyncSession,
    player_id: int,
    notification_type: NotificationType,
    event_type: NotificationEventType,
    other_player_id: int | None = None,
    scores: float | None = None,
    sector_id: int | None = None,
    game_title: str | None = None,
    card_name: str | None = None,
    event_end_time: int | None = None,
    message_text: str | None = None,
) -> None:
    notification = Notification(
        player_id=player_id,
        notification_type=notification_type.value,
        event_type=event_type.value,
        other_player_id=other_player_id,
        scores=scores,
        sector_id=sector_id,
        game_title=game_title,
        card_name=card_name,
        event_end_time=event_end_time,
        message_text=message_text,
        created_at=utc_now_ts(),
    )

    db.add(notification)
    await safe_commit(db)


async def create_game_completed_notification(
    db: AsyncSession, player_id: int, scores: float, game_title: str
) -> None:
    await create_notification(
        db=db,
        player_id=player_id,
        notification_type=NotificationType.STANDARD,
        event_type=NotificationEventType.GAME_COMPLETED,
        scores=scores,
        game_title=game_title,
    )


async def create_game_reroll_notification(
    db: AsyncSession, player_id: int, game_title: str
) -> None:
    await create_notification(
        db=db,
        player_id=player_id,
        notification_type=NotificationType.STANDARD,
        event_type=NotificationEventType.GAME_REROLL,
        game_title=game_title,
    )


async def create_game_drop_notification(
    db: AsyncSession, player_id: int, game_title: str
) -> None:
    await create_notification(
        db=db,
        player_id=player_id,
        notification_type=NotificationType.STANDARD,
        event_type=NotificationEventType.GAME_DROP,
        game_title=game_title,
    )


async def create_sector_tax_notification(
    db: AsyncSession, player_id: int, scores: float, sector_id: int
) -> None:
    await create_notification(
        db=db,
        player_id=player_id,
        notification_type=NotificationType.IMPORTANT,
        event_type=NotificationEventType.PAY_SECTOR_TAX,
        scores=scores,
        sector_id=sector_id,
    )


async def create_building_income_notification(
    db: AsyncSession,
    player_id: int,
    scores: float,
    other_player_id: int,
    sector_id: int,
) -> None:
    await create_notification(
        db=db,
        player_id=player_id,
        notification_type=NotificationType.IMPORTANT,
        event_type=NotificationEventType.BUILDING_INCOME,
        scores=scores,
        other_player_id=other_player_id,
        sector_id=sector_id,
    )


async def create_map_tax_notification(
    db: AsyncSession, player_id: int, scores: float
) -> None:
    await create_notification(
        db=db,
        player_id=player_id,
        notification_type=NotificationType.IMPORTANT,
        event_type=NotificationEventType.PAY_MAP_TAX,
        scores=scores,
    )


async def create_bonus_increase_notification(
    db: AsyncSession, player_id: int, scores: float
) -> None:
    await create_notification(
        db=db,
        player_id=player_id,
        notification_type=NotificationType.IMPORTANT,
        event_type=NotificationEventType.BONUS_INCREASE,
        scores=scores,
    )


async def create_card_stolen_notification(
    db: AsyncSession, player_id: int, card_name: str, other_player_id: int
) -> None:
    await create_notification(
        db=db,
        player_id=player_id,
        notification_type=NotificationType.STANDARD,
        event_type=NotificationEventType.CARD_STOLEN,
        card_name=card_name,
        other_player_id=other_player_id,
    )


async def create_card_lost_notification(
    db: AsyncSession, player_id: int, card_name: str, other_player_id: int
) -> None:
    await create_notification(
        db=db,
        player_id=player_id,
        notification_type=NotificationType.IMPORTANT,
        event_type=NotificationEventType.CARD_LOST,
        card_name=card_name,
        other_player_id=other_player_id,
    )


async def create_all_players_notification(
    db: AsyncSession,
    notification_type: NotificationType,
    event_type: NotificationEventType,
    **kwargs,
) -> None:
    from sqlalchemy import select

    from src.db_models import User

    users_query = await db.execute(select(User).where(User.is_active == 1))
    users = users_query.scalars().all()

    for user in users:
        await create_notification(
            db=db,
            player_id=user.id,
            notification_type=notification_type,
            event_type=event_type,
            **kwargs,
        )


async def create_player_notification(
    db: AsyncSession,
    player_id: int,
    notification_type: NotificationType,
    event_type: NotificationEventType,
    **kwargs,
) -> None:
    from sqlalchemy import select

    from src.db_models import User

    user_query = await db.execute(
        select(User).where(User.id == player_id, User.is_active == 1)
    )
    user = user_query.scalar_one_or_none()
    if user:
        await create_notification(
            db=db,
            player_id=user.id,
            notification_type=notification_type,
            event_type=event_type,
            **kwargs,
        )


async def create_message_notification(
    db: AsyncSession,
    notification_type: NotificationType,
    message_text: str,
) -> None:
    await create_all_players_notification(
        db=db,
        notification_type=notification_type,
        event_type=NotificationEventType.MESSAGE,
        message_text=message_text,
    )


async def create_player_message_notification(
    db: AsyncSession,
    player_id: int,
    notification_type: NotificationType,
    message_text: str,
) -> None:
    await create_player_notification(
        db=db,
        player_id=player_id,
        notification_type=notification_type,
        event_type=NotificationEventType.MESSAGE,
        message_text=message_text,
    )
