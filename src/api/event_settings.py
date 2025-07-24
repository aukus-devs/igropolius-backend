from typing import Annotated

from fastapi import APIRouter, Depends
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

    return EventSettingsResponse(settings=settings_dict)
