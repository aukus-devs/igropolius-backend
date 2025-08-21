import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import CurrentUserResponse, LoginRequest, LoginResponse
from src.db.db_models import BonusCard, DiceRoll, User
from src.db.db_session import get_db
from src.utils.auth import get_current_user
from src.utils.jwt import create_access_token, verify_password

router = APIRouter(tags=["auth"])


@router.post("/api/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
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


@router.get("/api/players/current", response_model=CurrentUserResponse)
async def fetch_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing_roll_query = await db.execute(
        select(DiceRoll)
        .where(DiceRoll.player_id == current_user.id, DiceRoll.used == 0)
        .order_by(DiceRoll.created_at.desc())
        .limit(1)
    )
    existing_roll = existing_roll_query.scalars().first()
    response = CurrentUserResponse.model_validate(current_user)
    if existing_roll:
        response.last_roll_result = json.loads(existing_roll.dice_values)

    bonus_cards_query = select(BonusCard)
    bonus_cards_result = await db.execute(bonus_cards_query)
    bonus_cards = bonus_cards_result.scalars().all()
    response.bonus_cards = bonus_cards
    return response
