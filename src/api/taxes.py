from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import PayTaxRequest
from src.consts import (
    MAP_TAX_PERCENT,
    SCORES_BY_GAME_LENGTH,
    STREET_INCOME_MULTILIER,
    STREET_TAX_PAYER_MULTILIER,
)
from src.db import get_db
from src.db_models import PlayerGame, PlayerScoreChange, User
from src.enums import GameCompletionType, ScoreChangeType, TaxType
from src.utils.auth import get_current_user_for_update
from src.utils.db import safe_commit
from src.utils.notifications import (
    create_building_income_notification,
    create_map_tax_notification,
    create_sector_tax_notification,
)

router = APIRouter(tags=["taxes"])


@router.post("/api/players/current/pay-taxes")
async def pay_tax(
    request: PayTaxRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if request.tax_type == TaxType.MAP_TAX:
        # tax is 5% from current player score
        tax_amount = current_user.total_score * MAP_TAX_PERCENT
        tax_amount = round(tax_amount, 2)
        score_change = PlayerScoreChange(
            player_id=current_user.id,
            score_change=-tax_amount,
            change_type=ScoreChangeType.MAP_TAX.value,
            description="map tax 5%",
            sector_id=current_user.sector_id,
        )
        current_user.total_score -= tax_amount
        current_user.total_score = round(current_user.total_score, 2)
        db.add(score_change)

        await create_map_tax_notification(db, current_user.id, tax_amount)

        await safe_commit(db)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if request.tax_type == TaxType.STREET_TAX:
        games_query = await db.execute(
            select(PlayerGame)
            .where(PlayerGame.sector_id == current_user.sector_id)
            .where(PlayerGame.player_id != current_user.id)
            .where(PlayerGame.type == GameCompletionType.COMPLETED.value)
        )
        games = games_query.scalars().all()
        tax_payments: list[float] = []
        for game in games:
            tax_amount = (
                SCORES_BY_GAME_LENGTH.get(game.item_length, 0) * STREET_INCOME_MULTILIER
            )
            tax_payments.append(tax_amount)

            score_change = PlayerScoreChange(
                player_id=game.player_id,
                score_change=tax_amount,
                change_type=ScoreChangeType.STREET_INCOME.value,
                description=f"street income from {current_user.username} for '{game.item_title}'",
                sector_id=current_user.sector_id,
            )
            db.add(score_change)

            await create_building_income_notification(
                db, game.player_id, tax_amount, current_user.id, current_user.sector_id
            )

        total_tax = sum(tax_payments) * STREET_TAX_PAYER_MULTILIER
        score_change = PlayerScoreChange(
            player_id=current_user.id,
            score_change=-total_tax,
            change_type=ScoreChangeType.STREET_TAX.value,
            description=f"street tax for {len(games)} games",
            sector_id=current_user.sector_id,
        )
        db.add(score_change)
        current_user.total_score -= total_tax
        current_user.total_score = round(current_user.total_score, 2)

        await create_sector_tax_notification(
            db, current_user.id, total_tax, current_user.sector_id
        )

        await safe_commit(db)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid tax type",
    )
