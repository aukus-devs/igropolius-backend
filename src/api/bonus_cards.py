from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import (
    GiveBonusCard,
    GiveBonusCardResponse,
    LoseBonusCardRequest,
    StealBonusCardRequest,
    UseBonusCardRequest,
    UseInstantCardRequest,
    UseInstantCardResponse,
)
from src.db.db_session import get_db
from src.db.db_models import PlayerCard, PlayerScoreChange, User
from src.db.queries.players import get_players_by_score
from src.enums import (
    InstantCardResult,
    InstantCardType,
    MainBonusCardType,
    ScoreChangeType,
)
from src.utils.auth import get_current_user, get_current_user_for_update
from src.utils.db import safe_commit, utc_now_ts
from src.db.queries.notifications import (
    create_card_lost_notification,
    create_card_stolen_notification,
)

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

    await create_card_stolen_notification(
        db, current_user.id, request.bonus_type.value, request.player_id
    )
    await create_card_lost_notification(
        db, request.player_id, request.bonus_type.value, current_user.id
    )

    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/bonus-cards/use")
async def use_bonus_card(
    request: UseBonusCardRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    cards_query = await db.execute(
        select(PlayerCard)
        .where(PlayerCard.player_id == current_user.id)
        .where(PlayerCard.status == "active")
        .where(PlayerCard.card_type == request.bonus_type.value)
        .with_for_update()
    )
    card = cards_query.scalars().first()

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active bonus card found",
        )

    card.status = "used"
    card.used_at = utc_now_ts()
    card.used_on_sector = current_user.sector_id

    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/bonus-cards/lose")
async def lose_bonus_card(
    request: LoseBonusCardRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    cards_query = await db.execute(
        select(PlayerCard)
        .where(PlayerCard.player_id == current_user.id)
        .where(PlayerCard.status == "active")
        .where(PlayerCard.card_type == request.bonus_type.value)
        .with_for_update()
    )
    card = cards_query.scalars().first()

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active bonus card found",
        )

    card.status = "lost"
    card.lost_at = utc_now_ts()
    card.lost_on_sector = current_user.sector_id

    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/bonus-cards/instant", response_model=UseInstantCardResponse)
async def use_instant_card(
    request: UseInstantCardRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    response = UseInstantCardResponse()
    match request.card_type:
        case InstantCardType.RECEIVE_3_PERCENT:
            score_change = current_user.total_score * 0.03
            current_user.total_score += score_change
            change = PlayerScoreChange(
                player_id=current_user.id,
                score_change=score_change,
                change_type=ScoreChangeType.INSTANT_CARD.value,
                description="Received 3% bonus from instant card",
                sector_id=current_user.sector_id,
            )
            db.add(change)
        case InstantCardType.RECEIVE_1_PERCENT_PLUS_20:
            score_change = current_user.total_score * 0.01 + 20
            current_user.total_score += score_change
            change = PlayerScoreChange(
                player_id=current_user.id,
                score_change=score_change,
                change_type=ScoreChangeType.INSTANT_CARD.value,
                description="Received 1% bonus plus 20 from instant card",
                sector_id=current_user.sector_id,
            )
            db.add(change)
        case InstantCardType.LOSE_2_PERCENTS:
            score_change = current_user.total_score * 0.02
            current_user.total_score -= score_change
            change = PlayerScoreChange(
                player_id=current_user.id,
                score_change=-score_change,
                change_type=ScoreChangeType.INSTANT_CARD.value,
                description="Lost 2% from instant card",
                sector_id=current_user.sector_id,
            )
            db.add(change)
        case InstantCardType.RECEIVE_SCORES_FOR_PLACE:
            players = await get_players_by_score(db)
            score_change = 0
            for i, player in enumerate(players):
                if player.id == current_user.id:
                    score_change = current_user.total_score * 0.01 * (i + 1)
                    current_user.total_score += score_change
                    change = PlayerScoreChange(
                        player_id=current_user.id,
                        score_change=score_change,
                        change_type=ScoreChangeType.INSTANT_CARD.value,
                        description=f"Received scores for place {i + 1} from instant card",
                        sector_id=current_user.sector_id,
                    )
                    db.add(change)
                    break

        case InstantCardType.RECEIVE_1_PERCENT_FROM_ALL:
            players = await get_players_by_score(db, for_update=True)
            score_change = 0
            for player in players:
                if player.id != current_user.id:
                    amount = player.total_score * 0.01
                    score_change += amount
                    player.total_score -= amount
                    player_change = PlayerScoreChange(
                        player_id=player.id,
                        score_change=-amount,
                        change_type=ScoreChangeType.INSTANT_CARD.value,
                        description=f"Lost 1% to {current_user.username} from instant card",
                        sector_id=player.sector_id,
                    )
                    db.add(player_change)

            current_user.total_score += score_change
            change = PlayerScoreChange(
                player_id=current_user.id,
                score_change=score_change,
                change_type=ScoreChangeType.INSTANT_CARD.value,
                description="Received 1% from all players from instant card",
                sector_id=current_user.sector_id,
            )
            db.add(change)
        case InstantCardType.LEADERS_LOSE_PERCENTS:
            players = await get_players_by_score(db, for_update=True)
            for i, player in enumerate(players[:3]):
                amount = player.total_score * 0.01 * (3 - i)
                player.total_score -= amount
                change = PlayerScoreChange(
                    player_id=player.id,
                    score_change=-amount,
                    change_type=ScoreChangeType.INSTANT_CARD.value,
                    description=f"Leader lost {3 - i}% from instant card",
                    sector_id=current_user.sector_id,
                )
                db.add(change)

        case InstantCardType.RECEIVE_5_PERCENT_OR_REROLL:
            players = await get_players_by_score(db)
            for i, player in enumerate(players):
                if player.id == current_user.id:
                    if i < len(players) / 2:
                        response.result = InstantCardResult.REROLL
                    else:
                        score_change = player.total_score * 0.05
                        current_user.total_score += score_change
                        change = PlayerScoreChange(
                            player_id=current_user.id,
                            score_change=score_change,
                            change_type=ScoreChangeType.INSTANT_CARD.value,
                            description="Received 5% bonus for losing from instant card",
                            sector_id=current_user.sector_id,
                        )
                        db.add(change)
                    break
        case InstantCardType.LOSE_CARD_OR_3_PERCENT:
            if request.card_to_lose is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Card to lose must be specified",
                )

            cards_query = await db.execute(
                select(PlayerCard)
                .where(PlayerCard.player_id == current_user.id)
                .where(PlayerCard.status == "active")
                .where(PlayerCard.card_type == request.card_to_lose.value)
                .with_for_update()
            )
            card = cards_query.scalars().first()
            if not card:
                score_change = current_user.total_score * 0.03
                current_user.total_score -= score_change
                change = PlayerScoreChange(
                    player_id=current_user.id,
                    score_change=-score_change,
                    change_type=ScoreChangeType.INSTANT_CARD.value,
                    description="Lost 3% for not losing a card",
                    sector_id=current_user.sector_id,
                )
                db.add(change)
                response.result = InstantCardResult.SCORES_LOST
            else:
                card.status = "lose"
                card.lost_at = utc_now_ts()
                card.lost_on_sector = current_user.sector_id
                response.result = InstantCardResult.CARD_LOST
        case InstantCardType.REROLL:
            response.result = InstantCardResult.REROLL
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid instant card type",
            )

    bonus_card = PlayerCard(
        player_id=current_user.id,
        card_type=request.card_type.value,
        received_on_sector=current_user.sector_id,
        status="used",
        used_at=utc_now_ts(),
        used_on_sector=current_user.sector_id,
    )
    db.add(bonus_card)

    await safe_commit(db)
    return response
