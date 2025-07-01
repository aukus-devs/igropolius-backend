from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import (
    CreateAllPlayersNotificationRequest,
    CreateMessageNotificationRequest,
    CreateNotificationResponse,
    CreatePlayerMessageNotificationRequest,
    CreatePlayerNotificationRequest,
    SetEventEndTimeRequest,
    StreamCheckResponse,
)
from src.db import get_db
from src.db_models import EventSettings, User
from src.enums import NotificationEventType, NotificationType, Role
from src.utils.auth import get_current_user, get_current_user_direct
from src.utils.db import safe_commit
from src.utils.notifications import (
    create_all_players_notification,
    create_message_notification,
    create_player_message_notification,
    create_player_notification,
)

router = APIRouter(tags=["internal"])


@router.get("/api/streams/refresh", response_model=StreamCheckResponse)
async def refresh_streams(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from src.stream_checker import refresh_stream_statuses

    try:
        stats = await refresh_stream_statuses(db)

        if stats.get("errors"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"success": False, "stats": stats},
            )

        return StreamCheckResponse(success=True, stats=stats)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "stats": {}},
        )


@router.post("/api/internal/reset-db")
async def reset_internal(
    current_user: Annotated[User, Depends(get_current_user_direct)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )

    from src.utils.db import reset_database

    await reset_database(db)
    await safe_commit(db)

    return {"success": True, "message": "Database has been reset successfully."}


@router.post(
    "/api/internal/notifications/event-ending-soon",
    response_model=CreateNotificationResponse,
)
async def create_event_ending_soon_notification_for_all(
    current_user: Annotated[User, Depends(get_current_user_direct)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )

    try:
        event_settings_query = await db.execute(
            select(EventSettings).order_by(EventSettings.updated_at.desc()).limit(1)
        )
        event_settings = event_settings_query.scalars().first()

        if not event_settings or not event_settings.event_end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event end time is not configured",
            )

        await create_all_players_notification(
            db=db,
            notification_type=NotificationType.IMPORTANT,
            event_type=NotificationEventType.EVENT_ENDING_SOON,
            event_end_time=event_settings.event_end_time,
        )

        return CreateNotificationResponse(
            success=True, message="Event ending soon notification sent to all players"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notifications: {str(e)}",
        )


@router.post(
    "/api/internal/notifications/all-players", response_model=CreateNotificationResponse
)
async def create_notification_for_all_players(
    request: CreateAllPlayersNotificationRequest,
    current_user: Annotated[User, Depends(get_current_user_direct)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )

    try:
        await create_all_players_notification(
            db=db,
            notification_type=request.notification_type,
            event_type=request.event_type,
            other_player_id=request.other_player_id,
            scores=request.scores,
            sector_id=request.sector_id,
            game_title=request.game_title,
            card_name=request.card_name,
            event_end_time=request.event_end_time,
            message_text=request.message_text,
        )

        return CreateNotificationResponse(
            success=True,
            message=f"Notification ({request.event_type.value}) sent to all players",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notifications: {str(e)}",
        )


@router.post(
    "/api/internal/notifications/player", response_model=CreateNotificationResponse
)
async def create_notification_for_player(
    request: CreatePlayerNotificationRequest,
    current_user: Annotated[User, Depends(get_current_user_direct)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )

    try:
        await create_player_notification(
            db=db,
            player_id=request.player_id,
            notification_type=request.notification_type,
            event_type=request.event_type,
            other_player_id=request.other_player_id,
            scores=request.scores,
            sector_id=request.sector_id,
            game_title=request.game_title,
            card_name=request.card_name,
            event_end_time=request.event_end_time,
            message_text=request.message_text,
        )

        return CreateNotificationResponse(
            success=True,
            message=f"Notification ({request.event_type.value}) sent to player {request.player_id}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}",
        )


@router.post(
    "/api/internal/notifications/message", response_model=CreateNotificationResponse
)
async def send_message_to_all_players(
    request: CreateMessageNotificationRequest,
    current_user: Annotated[User, Depends(get_current_user_direct)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )

    try:
        await create_message_notification(
            db=db,
            notification_type=request.notification_type,
            message_text=request.message_text,
        )

        return CreateNotificationResponse(
            success=True, message="Text message sent to all players"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}",
        )


@router.post(
    "/api/internal/notifications/message/player",
    response_model=CreateNotificationResponse,
)
async def send_message_to_player(
    request: CreatePlayerMessageNotificationRequest,
    current_user: Annotated[User, Depends(get_current_user_direct)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )

    try:
        await create_player_message_notification(
            db=db,
            player_id=request.player_id,
            notification_type=request.notification_type,
            message_text=request.message_text,
        )

        return CreateNotificationResponse(
            success=True, message=f"Text message sent to player {request.player_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}",
        )


@router.post("/api/internal/event-end-time", response_model=CreateNotificationResponse)
async def set_event_end_time(
    request: SetEventEndTimeRequest,
    current_user: Annotated[User, Depends(get_current_user_direct)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )

    try:
        event_settings_query = await db.execute(
            select(EventSettings).order_by(EventSettings.updated_at.desc()).limit(1)
        )
        event_settings = event_settings_query.scalars().first()

        if event_settings:
            event_settings.event_end_time = request.event_end_time
        else:
            event_settings = EventSettings(event_end_time=request.event_end_time)
            db.add(event_settings)

        await safe_commit(db)

        message = (
            f"Event end time set to {request.event_end_time}"
            if request.event_end_time
            else "Event end time cleared"
        )

        return CreateNotificationResponse(success=True, message=message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set event end time: {str(e)}",
        )
