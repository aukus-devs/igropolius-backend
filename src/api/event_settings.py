from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import EventSettingsResponse
from src.db.db_models import EventSettings
from src.db.db_session import get_db

router = APIRouter(tags=["event-settings"])


@router.get("/api/event-settings", response_model=EventSettingsResponse)
async def get_event_settings(db: Annotated[AsyncSession, Depends(get_db)]):
    settings_query = await db.execute(select(EventSettings))
    settings_records = settings_query.scalars().all()

    settings_dict = {record.key_name: record.value for record in settings_records}

    required_settings = ["event_start_time", "event_end_time"]
    missing_settings = [
        setting
        for setting in required_settings
        if setting not in settings_dict or settings_dict[setting] is None
    ]

    if missing_settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required settings: {', '.join(missing_settings)}",
        )

    return EventSettingsResponse(settings=settings_dict)
