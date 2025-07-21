from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import (
    GiveBonusCardRequest,
    GiveBonusCardResponse,
    DropBonusCardRequest,
    StealBonusCardRequest,
    UseBonusCardRequest,
    UseInstantCardRequest,
    UseInstantCardResponse,
)
from src.db.db_session import get_db
from src.db.db_models import PlayerCard, PlayerMove, User
from src.db.queries.players import change_player_score, get_players_by_score
from src.enums import (
    BonusCardStatus,
    InstantCardResult,
    InstantCardType,
    MainBonusCardType,
    PlayerMoveType,
    PlayerTurnState,
    Role,
    ScoreChangeType,
)
from src.utils.auth import get_current_user, get_current_user_for_update
from src.utils.common import get_closest_prison_sector
from src.utils.db import utc_now_ts
from src.db.queries.notifications import (
    create_card_lost_notification,
    create_card_stolen_notification,
)

router = APIRouter(tags=["bonus_cards"])


@router.post("/api/bonus-cards", response_model=GiveBonusCardResponse)
async def receive_bonus_card(
    request: GiveBonusCardRequest,
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

    if current_user.turn_state == PlayerTurnState.ENTERING_PRISON.value:
        # remove card from prison
        prison_query = (
            select(User)
            .where(User.role == Role.PRISON.value)
            .where(User.is_active == 1)
        )
        prison = await db.execute(prison_query)
        prison_user = prison.scalars().first()
        if not prison_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Prison user not found",
            )
        prison_cards_query = (
            select(PlayerCard)
            .where(PlayerCard.player_id == prison_user.id)
            .where(PlayerCard.status == "active")
            .where(PlayerCard.card_type == card)
        )
        prison_cards = await db.execute(prison_cards_query)
        prison_card = prison_cards.scalars().first()
        if not prison_card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prison card not found",
            )
        prison_card.status = BonusCardStatus.DROPPED.value
        prison_card.lost_at = utc_now_ts()
        prison_card.lost_on_sector = current_user.sector_id

    await db.flush()

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

    card.status = BonusCardStatus.STOLEN.value
    card.stolen_at = utc_now_ts()
    card.stolen_by = current_user.id

    new_card = PlayerCard(
        player_id=current_user.id,
        card_type=card.card_type,
        received_on_sector=current_user.sector_id,
        stolen_from_player=request.player_id,
        status=BonusCardStatus.ACTIVE.value,
    )
    db.add(new_card)

    await create_card_stolen_notification(
        db, current_user.id, request.bonus_type.value, request.player_id
    )
    await create_card_lost_notification(
        db, request.player_id, request.bonus_type.value, current_user.id
    )

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
        .where(PlayerCard.status == BonusCardStatus.ACTIVE.value)
        .where(PlayerCard.card_type == request.bonus_type.value)
        .with_for_update()
    )
    card = cards_query.scalars().first()

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active bonus card found",
        )

    card.status = BonusCardStatus.USED.value
    card.used_at = utc_now_ts()
    card.used_on_sector = current_user.sector_id

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/bonus-cards/lose")
async def drop_bonus_card(
    request: DropBonusCardRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    cards_query = await db.execute(
        select(PlayerCard)
        .where(PlayerCard.player_id == current_user.id)
        .where(PlayerCard.status == BonusCardStatus.ACTIVE.value)
        .where(PlayerCard.card_type == request.bonus_type.value)
        .with_for_update()
    )
    card = cards_query.scalars().first()

    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active bonus card found",
        )

    card.status = BonusCardStatus.DROPPED.value
    card.lost_at = utc_now_ts()
    card.lost_on_sector = current_user.sector_id

    match current_user.turn_state:
        case PlayerTurnState.ENTERING_PRISON.value:
            # move the card to prison storage
            prison_query = (
                select(User)
                .where(User.role == Role.PRISON.value)
                .where(User.is_active == 1)
            )
            prison = await db.execute(prison_query)
            prison_user = prison.scalars().first()
            if not prison_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Prison user not found",
                )
            new_card = PlayerCard(
                player_id=prison_user.id,
                card_type=card.card_type,
                received_on_sector=current_user.sector_id,
                status=BonusCardStatus.ACTIVE.value,
            )
            db.add(new_card)
        case PlayerTurnState.DROPPING_CARD_AFTER_GAME_DROP.value:
            # move player to prison
            prison_sector = get_closest_prison_sector(current_user.sector_id)
            prison_move = PlayerMove(
                player_id=current_user.id,
                sector_from=current_user.sector_id,
                sector_to=get_closest_prison_sector(current_user.sector_id),
                move_type=PlayerMoveType.DROP_TO_PRISON.value,
                map_completed=False,
                adjusted_roll=prison_sector - current_user.sector_id,
                random_org_roll=-1,
            )
            db.add(prison_move)
            current_user.sector_id = prison_sector
        case PlayerTurnState.DROPPING_CARD_AFTER_INSTANT_ROLL.value:
            pass
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot lose bonus card in current turn state: {current_user.turn_state}",
            )

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
            change = current_user.total_score * 0.03
            await change_player_score(
                db,
                current_user,
                change,
                ScoreChangeType.INSTANT_CARD,
                "Received 3% bonus from instant card",
            )
        case InstantCardType.RECEIVE_1_PERCENT_PLUS_20:
            change = current_user.total_score * 0.01 + 20
            await change_player_score(
                db,
                current_user,
                change,
                ScoreChangeType.INSTANT_CARD,
                "Received 1% bonus plus 20 from instant card",
            )
        case InstantCardType.LOSE_2_PERCENTS:
            change = current_user.total_score * 0.02
            await change_player_score(
                db,
                current_user,
                -change,
                ScoreChangeType.INSTANT_CARD,
                "Lost 2% from instant card",
            )
        case InstantCardType.RECEIVE_SCORES_FOR_PLACE:
            players = await get_players_by_score(db)
            receive_total = 0
            for i, player in enumerate(players):
                if player.id == current_user.id:
                    change = current_user.total_score * 0.01 * (i + 1)
                    await change_player_score(
                        db,
                        current_user,
                        change,
                        ScoreChangeType.INSTANT_CARD,
                        f"Received scores for place {i + 1} from instant card",
                    )
                    break
        case InstantCardType.RECEIVE_1_PERCENT_FROM_ALL:
            players = await get_players_by_score(db, for_update=True)
            receive_total = 0
            for player in players:
                if player.id != current_user.id:
                    change = player.total_score * 0.01
                    await change_player_score(
                        db,
                        player,
                        -change,
                        ScoreChangeType.INSTANT_CARD,
                        f"Lost 1% to {current_user.username} from instant card",
                    )
                    receive_total += change

            await change_player_score(
                db,
                current_user,
                receive_total,
                ScoreChangeType.INSTANT_CARD,
                "Received 1% from all players from instant card",
            )
        case InstantCardType.LEADERS_LOSE_PERCENTS:
            players = await get_players_by_score(db, for_update=True, limit=3)
            for i, player in enumerate(players):
                change = player.total_score * 0.01 * (3 - i)
                await change_player_score(
                    db,
                    player,
                    -change,
                    ScoreChangeType.INSTANT_CARD,
                    f"Leader lost {3 - i}% from instant card",
                )

        case InstantCardType.RECEIVE_5_PERCENT_OR_REROLL:
            players = await get_players_by_score(db)
            for i, player in enumerate(players):
                if player.id == current_user.id:
                    if i < len(players) / 2:
                        response.result = InstantCardResult.REROLL
                    else:
                        change = player.total_score * 0.05
                        await change_player_score(
                            db,
                            current_user,
                            change,
                            ScoreChangeType.INSTANT_CARD,
                            "Received 5% bonus for losing from instant card",
                        )
                        response.result = InstantCardResult.SCORES_RECEIVED
                    break
        case InstantCardType.LOSE_CARD_OR_3_PERCENT:
            card_to_lose = None
            if request.card_to_lose:
                cards_query = await db.execute(
                    select(PlayerCard)
                    .where(PlayerCard.player_id == current_user.id)
                    .where(PlayerCard.status == BonusCardStatus.ACTIVE.value)
                    .where(PlayerCard.card_type == request.card_to_lose.value)
                    .with_for_update()
                )
                card_to_lose = cards_query.scalars().first()

            if card_to_lose:
                card_to_lose.status = BonusCardStatus.DROPPED.value
                card_to_lose.lost_at = utc_now_ts()
                card_to_lose.lost_on_sector = current_user.sector_id
                response.result = InstantCardResult.CARD_LOST
            else:
                cards_query = await db.execute(
                    select(PlayerCard)
                    .where(PlayerCard.player_id == current_user.id)
                    .where(PlayerCard.status == BonusCardStatus.ACTIVE.value)
                )
                cards = cards_query.scalars().all()
                if not cards:
                    change = current_user.total_score * 0.03
                    await change_player_score(
                        db,
                        current_user,
                        -change,
                        ScoreChangeType.INSTANT_CARD,
                        "Lost 3% for not losing a card",
                    )
                    response.result = InstantCardResult.SCORES_LOST
                else:
                    response.result = InstantCardResult.REROLL
        case InstantCardType.REROLL:
            response.result = InstantCardResult.REROLL
        case InstantCardType.REROLL_AND_ROLL:
            pass
        case InstantCardType.DOWNGRADE_NEXT_BUILDING:
            if current_user.has_downgrade_bonus:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You already have a downgrade bonus",
                )
            if current_user.has_upgrade_bonus:
                current_user.has_upgrade_bonus = False
            else:
                current_user.has_downgrade_bonus = True
        case InstantCardType.UPGRADE_NEXT_BUILDING:
            if current_user.has_upgrade_bonus:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You already have an upgrade bonus",
                )
            if current_user.has_downgrade_bonus:
                current_user.has_downgrade_bonus = False
            else:
                current_user.has_upgrade_bonus = True
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid instant card type",
            )

    bonus_card = PlayerCard(
        player_id=current_user.id,
        card_type=request.card_type.value,
        received_on_sector=current_user.sector_id,
        status=BonusCardStatus.USED.value,
        used_at=utc_now_ts(),
        used_on_sector=current_user.sector_id,
    )
    db.add(bonus_card)

    return response
