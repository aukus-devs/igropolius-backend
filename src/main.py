from src.consts import SCORES_BY_GAME_LENGTH
from datetime import datetime
from typing import Annotated
import json

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.params import Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import (
    GiveBonusCard,
    IgdbGamesList,
    PayTaxRequest,
    RollDiceRequest,
    RollDiceResponse,
    SavePlayerGame,
    StreamCheckResponse,
    StealBonusCardRequest,
    UpdatePlayerTurnState,
)
from src.db import get_db
from src.db_models import (
    IgdbGame,
    PlayerCard,
    PlayerGame,
    PlayerScoreChange,
    User,
    DiceRoll,
)
from src.enums import (
    GameCompletionType,
    ScoreChangeType,
    TaxType,
)
from src.utils.auth import get_current_user
from src.utils.db import safe_commit
from src.utils.category_history import (
    calculate_game_duration_by_title,
    save_category_history,
)
from src.consts import STREET_INCOME_MULTILIER
from src.consts import STREET_TAX_PAYER_MULTILIER
from src.utils.random_org import get_random_numbers
from src.api import auth, players, rules

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://igropolus.onrender.com",
        "https://igropolius.ru",
        "http://localhost:5200",
    ],  # Adjust as needed for production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],  # Adjust as needed for production
)

app.include_router(auth.router)
app.include_router(players.router)
app.include_router(rules.router)


@app.post("/api/dice/roll", response_model=RollDiceResponse)
async def roll_dice(
    request: RollDiceRequest,
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

    if existing_roll:
        return RollDiceResponse(
            roll_id=existing_roll.id,
            is_random_org_result=bool(existing_roll.is_random_org_result),
            random_org_check_form=existing_roll.random_org_check_url,
            data=json.loads(existing_roll.dice_values),
        )

    random_result = await get_random_numbers(
        request.num, request.min, request.max, current_user.id
    )

    dice_roll = DiceRoll(
        player_id=current_user.id,
        used=0,
        is_random_org_result=1 if random_result["is_random_org_result"] else 0,
        json_short_data=json.dumps(
            {
                "is_random_org_result": random_result["is_random_org_result"],
                "random_org_check_form": random_result["random_org_check_form"],
                "data": random_result["data"],
            }
        ),
        random_org_result=random_result["random_org_result"],
        dice_values=json.dumps(random_result["data"]),
        random_org_check_url=random_result["random_org_check_form"],
    )

    db.add(dice_roll)

    await safe_commit(db)

    return RollDiceResponse(
        roll_id=dice_roll.id,
        is_random_org_result=random_result["is_random_org_result"],
        random_org_check_form=random_result["random_org_check_form"],
        data=random_result["data"],
    )


@app.post("/api/players/current/turn-state")
async def update_turn_state(
    request: UpdatePlayerTurnState,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user.turn_state = request.turn_state.value
    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/player-games")
async def save_player_game(
    request: SavePlayerGame,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        game_duration = await calculate_game_duration_by_title(
            db, request.title, current_user.id
        )
    except Exception:
        game_duration = 0

    game = PlayerGame(
        player_id=current_user.id,
        type=request.status.value,
        item_title=request.title,
        item_review=request.review,
        item_rating=request.rating,
        item_length=request.length,
        vod_links=request.vod_links,
        sector_id=current_user.sector_id,
        game_id=request.game_id,
        duration=game_duration,
    )
    db.add(game)

    score_change = PlayerScoreChange(
        player_id=current_user.id,
        score_change=request.scores,
        change_type=ScoreChangeType.GAME_COMPLETED.value,
        description=f"game completed: '{request.title}'",
        sector_id=current_user.sector_id,
    )
    db.add(score_change)

    current_user.total_score += request.scores
    current_user.current_game = None
    current_user.current_game_updated_at = None
    current_user.current_game_cover = None
    await save_category_history(db, current_user.id, "NewPlayerGame")

    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/players/current/pay-taxes")
async def pay_tax(
    request: PayTaxRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if request.tax_type == TaxType.MAP_TAX:
        # tax is 5% from current player score
        tax_amount = current_user.total_score * 0.05
        score_change = PlayerScoreChange(
            player_id=current_user.id,
            score_change=-tax_amount,
            change_type=ScoreChangeType.MAP_TAX.value,
            description="map tax 5%",
            sector_id=current_user.sector_id,
        )
        current_user.total_score -= tax_amount
        db.add(score_change)
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
        await safe_commit(db)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid tax type",
    )


@app.get("/api/igdb/games/search", response_model=IgdbGamesList)
async def search_igdb_games_get(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    query: str,
    limit: int = 20,
):
    from sqlalchemy import case

    query = query.strip()

    search_query = (
        select(IgdbGame)
        .where(IgdbGame.name.ilike(f"%{query}%"))
        .order_by(case((IgdbGame.name.ilike(f"{query}%"), 0), else_=1), IgdbGame.name)
        .limit(limit)
    )

    result = await db.execute(search_query)
    games = result.scalars().all()

    return {"games": games}


@app.get("/api/igdb/games/{game_id}")
async def get_igdb_game(
    game_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    query = select(IgdbGame).where(IgdbGame.id == game_id)
    result = await db.execute(query)
    game = result.scalars().first()

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    return game


@app.post("/api/bonus-cards")
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
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/bonus-cards/steal")
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
    card.stolen_at = round(datetime.now().timestamp())
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


@app.get("/api/streams/refresh", response_model=StreamCheckResponse)
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
