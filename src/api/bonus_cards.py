from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api_models import GiveBonusCard, GiveBonusCardResponse, StealBonusCardRequest
from src.db import get_db
from src.db_models import PlayerCard, User
from src.enums import MainBonusCardType
from src.utils.auth import get_current_user
from src.utils.db import safe_commit, utc_now_ts


router = APIRouter(tags=["bonus_cards"])


@router.post("/api/bonus-cards", response_model=GiveBonusCardResponse)
async def receive_bonus_card(
    request: GiveBonusCard,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    cards_query = await db.execute(
        select(PlayerCard)
        .where(PlayerCard.player_id == current_user.id)
        .where(PlayerCard.status == "active")
    )
    cards = cards_query.scalars().all()
    card = request.bonus_type.value
    is_new_card = card not in [c.card_type for c in cards]

    if not is_new_card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bonus card already received",
        )

    new_card = PlayerCard(
        player_id=current_user.id,
        card_type=card,
        received_on_sector=current_user.sector_id,
        status="active",
    )
    db.add(new_card)
    await safe_commit(db)
    return GiveBonusCardResponse(
        bonus_type=MainBonusCardType(new_card.card_type),
        received_at=new_card.created_at,
        received_on_sector=new_card.received_on_sector,
    )


@router.post("/api/bonus-cards/steal")
async def steal_bonus_card(
    request: StealBonusCardRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if request.player_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot steal your own bonus card",
        )

    cards_query = await db.execute(
        select(PlayerCard)
        .where(PlayerCard.player_id == request.player_id)
        .where(PlayerCard.status == "active")
        .where(PlayerCard.card_type == request.bonus_type.value)
        .with_for_update()
    )
    card = cards_query.scalars().first()

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active bonus cards found for this player",
        )

    card.status = "stolen"
    card.stolen_at = utc_now_ts()
    card.stolen_by = current_user.id

    new_card = PlayerCard(
        player_id=current_user.id,
        card_type=card.card_type,
        received_on_sector=current_user.sector_id,
        stolen_from_player=request.player_id,
        status="active",
    )
    db.add(new_card)
    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
