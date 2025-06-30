from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api_models import StreamCheckResponse
from src.db import get_db
from src.db_models import User
from src.enums import Role
from src.utils.auth import get_current_user, get_current_user_direct
from src.utils.db import safe_commit


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
