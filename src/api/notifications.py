from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import (
    MarkNotificationsSeenRequest,
    NotificationItem,
    NotificationsResponse,
)
from src.db.db_models import Notification, User
from src.db.db_session import get_db
from src.enums import NotificationEventType
from src.utils.auth import get_current_user

router = APIRouter(tags=["notifications"])


@router.get("/api/notifications", response_model=NotificationsResponse)
async def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    notifications_query = await db.execute(
        select(Notification)
        .where(Notification.player_id == current_user.id, Notification.is_read == 0)
        .order_by(Notification.created_at.desc())
    )
    notifications = notifications_query.scalars().all()

    return NotificationsResponse(
        notifications=[
            NotificationItem(
                id=n.id,
                notification_type=n.notification_type,
                event_type=NotificationEventType(n.event_type),
                created_at=n.created_at,
                other_player_id=n.other_player_id,
                scores=n.scores,
                sector_id=n.sector_id,
                game_title=n.game_title,
                card_name=n.card_name,
                event_end_time=n.event_end_time,
                message_text=n.message_text,
            )
            for n in notifications
        ]
    )


@router.post("/api/notifications/seen")
async def mark_notifications_seen(
    request: MarkNotificationsSeenRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not request.notification_ids:
        return {"success": True}

    notifications_query = await db.execute(
        select(Notification).where(
            Notification.id.in_(request.notification_ids),
            Notification.player_id == current_user.id,
        )
    )
    notifications = notifications_query.scalars().all()

    if len(notifications) != len(request.notification_ids):
        raise HTTPException(
            status_code=400,
            detail="Some notifications not found or don't belong to current user",
        )

    await db.execute(
        update(Notification)
        .where(
            Notification.id.in_(request.notification_ids),
            Notification.player_id == current_user.id,
        )
        .values(is_read=1)
    )

    return {"success": True}
