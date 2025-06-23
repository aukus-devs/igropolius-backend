from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.params import Depends
from fastapi import APIRouter, HTTPException, Response, status

from src.api_models import CurrentUser, LoginRequest
from src.db import get_db
from src.db_models import User
from src.utils.auth import get_current_user
from src.utils.jwt import create_access_token, verify_password

router = APIRouter(tags=["auth"])


@router.post("/api/login")
async def login(
    request: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    query = await db.execute(select(User).filter(User.username == request.username))
    user = query.scalars().first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    token = create_access_token({"sub": user.username})
    return {"token": token}


@router.post("/api/logout")
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Invalidate the token or perform any necessary logout actions
    response.status_code = status.HTTP_204_NO_CONTENT
    return {"message": "Logged out successfully"}


@router.get("/api/players/current", response_model=CurrentUser)
def fetch_current_user(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
