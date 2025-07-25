import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import PayTaxRequest
from src.consts import (
    MAP_TAX_PERCENT,
    SCORES_BY_GAME_LENGTH,
    STREET_INCOME_GROUP_OWNER_MULTILIER,
    STREET_INCOME_MULTILIER,
    STREET_TAX_PAYER_MULTILIER,
)
from src.db.db_session import get_db
from src.db.db_models import PlayerGame, PlayerScoreChange, User
from src.db.queries.players import change_player_score
from src.enums import GameCompletionType, ScoreChangeType, TaxType
from src.utils.auth import get_current_user_for_update
from src.db.queries.notifications import (
    create_building_income_notification,
    create_map_tax_notification,
    create_sector_tax_notification,
)
from src.utils.common import find_sector_group, player_owns_sectors_group

router = APIRouter(tags=["taxes"])

logger = logging.getLogger(__name__)


@router.post("/api/players/current/pay-taxes")
async def pay_tax(
    request: PayTaxRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if request.tax_type == TaxType.MAP_TAX:
        # tax is 5% from current player score
        income_amount = round(current_user.total_score * MAP_TAX_PERCENT, 2)
        await change_player_score(
            db,
            player=current_user,
            score_change=-income_amount,
            change_type=ScoreChangeType.MAP_TAX,
            description="map tax 5%",
        )

        await create_map_tax_notification(db, current_user.id, income_amount)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if request.tax_type == TaxType.STREET_TAX:
        games_query = await db.execute(
            select(PlayerGame)
            .where(PlayerGame.sector_id == current_user.sector_id)
            .where(PlayerGame.player_id != current_user.id)
            .where(PlayerGame.type == GameCompletionType.COMPLETED.value)
        )
        games = list(games_query.scalars().all())
        if not games:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        players_query = await db.execute(
            select(User)
            .where(User.id.in_([game.player_id for game in games]))
            .with_for_update()
        )
        players = players_query.scalars().all()

        sector_group = find_sector_group(current_user.sector_id)
        tax_payments: list[float] = []
        for game in games:
            player = next((p for p in players if p.id == game.player_id), None)
            if not player:
                logger.error(
                    f"Player with ID {game.player_id} not found for game {game.id}"
                )
                continue

            multiplier = STREET_INCOME_MULTILIER
            if sector_group:
                owns_sector_group = await player_owns_sectors_group(
                    db, player, sector_group
                )
                if owns_sector_group:
                    multiplier = STREET_INCOME_GROUP_OWNER_MULTILIER

            income_amount = SCORES_BY_GAME_LENGTH.get(game.item_length, 0) * multiplier
            income_amount = round(income_amount, 2)
            tax_payments.append(income_amount)

            await change_player_score(
                db,
                player=player,
                score_change=income_amount,
                change_type=ScoreChangeType.STREET_INCOME,
                description=f"street income from {current_user.username} for '{game.item_title}'",
                income_from_player=current_user,
            )

            await create_building_income_notification(
                db,
                game.player_id,
                income_amount,
                current_user.id,
                current_user.sector_id,
            )

        total_tax = sum(tax_payments) * STREET_TAX_PAYER_MULTILIER
        await change_player_score(
            db,
            player=current_user,
            score_change=-total_tax,
            change_type=ScoreChangeType.STREET_TAX,
            description=f"street tax for {len(games)} games",
        )

        await create_sector_tax_notification(
            db, current_user.id, total_tax, current_user.sector_id
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid tax type",
    )
