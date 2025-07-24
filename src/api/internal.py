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
from src.db.db_models import EventSettings, User
from src.db.db_session import get_db
from src.db.queries.notifications import (
    create_all_players_notification,
    create_message_notification,
    create_player_message_notification,
    create_player_notification,
)
from src.enums import NotificationEventType, NotificationType, Role
from src.utils.auth import get_current_user, get_current_user_direct

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
        event_end_time_query = await db.execute(
            select(EventSettings).where(EventSettings.key_name == "event_end_time")
        )
        event_end_time_setting = event_end_time_query.scalars().first()

        if not event_end_time_setting or not event_end_time_setting.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event end time is not configured",
            )

        await create_all_players_notification(
            db=db,
            notification_type=NotificationType.IMPORTANT,
            event_type=NotificationEventType.EVENT_ENDING_SOON,
            event_end_time=int(event_end_time_setting.value),
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


@router.post("/api/internal/event-settings", response_model=CreateNotificationResponse)
async def set_event_settings(
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
        if request.event_start_time is not None:
            start_time_query = await db.execute(
                select(EventSettings)
                .where(EventSettings.key_name == "event_start_time")
                .with_for_update()
            )
            start_time_setting = start_time_query.scalars().first()

            if start_time_setting:
                start_time_setting.value = str(request.event_start_time)
            else:
                start_time_setting = EventSettings(
                    key="event_start_time", value=str(request.event_start_time)
                )
                db.add(start_time_setting)

        if request.event_end_time is not None:
            end_time_query = await db.execute(
                select(EventSettings)
                .where(EventSettings.key_name == "event_end_time")
                .with_for_update()
            )
            end_time_setting = end_time_query.scalars().first()

            if end_time_setting:
                end_time_setting.value = str(request.event_end_time)
            else:
                end_time_setting = EventSettings(
                    key="event_end_time", value=str(request.event_end_time)
                )
                db.add(end_time_setting)

        message = (
            f"Event end time set to {request.event_end_time}, start time set to {request.event_start_time}"
            if request.event_end_time or request.event_start_time
            else "Event times cleared"
        )

        return CreateNotificationResponse(success=True, message=message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event settings: {str(e)}",
        )
