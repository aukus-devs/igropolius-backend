from src.utils.common import map_bonus_card_to_event_type
from src.api_models import BonusCardEvent, GameEvent, ScoreChangeEvent
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
    BonusCard,
    CurrentUser,
    EventsList,
    GiveBonusCard,
    IgdbGamesList,
    IgdbGamesSearchRequest,
    LoginRequest,
    MakePlayerMove,
    MoveEvent,
    PayTaxRequest,
    RulesResponse,
    RulesVersion,
    SavePlayerGame,
    StreamCheckResponse,
    StealBonusCardRequest,
    UpdatePlayerTurnState,
    UserGame,
    UserSummary,
    UsersList,
)
from src.db import get_db
from src.db_models import (
    IgdbGame,
    PlayerCard,
    PlayerGame,
    PlayerMove,
    PlayerScoreChange,
    Rules,
    User,
)
from src.enums import (
    GameCompletionType,
    MainBonusCardType,
    PlayerMoveType,
    ScoreChangeType,
    TaxType,
)
from src.utils.auth import get_current_user
from src.utils.db import safe_commit
from src.utils.jwt import create_access_token, verify_password
from src.utils.category_history import get_current_game_duration, calculate_time_by_category_name
from typing_extensions import cast
from src.consts import STREET_INCOME_MULTILIER
from src.consts import STREET_TAX_PAYER_MULTILIER

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


@app.post("/api/login")
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


@app.post("/api/logout")
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Invalidate the token or perform any necessary logout actions
    response.status_code = status.HTTP_204_NO_CONTENT
    return {"message": "Logged out successfully"}


@app.get("/api/players/current", response_model=CurrentUser)
def fetch_current_user(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@app.get("/api/players", response_model=UsersList)
async def get_users(db: Annotated[AsyncSession, Depends(get_db)]):
    users_query = await db.execute(select(User).filter(User.is_active == 1))
    users = users_query.scalars().all()
    games_query = await db.execute(select(PlayerGame))
    games = games_query.scalars().all()
    cards_query = await db.execute(
        select(PlayerCard).where(PlayerCard.status == "active")
    )
    cards = cards_query.scalars().all()

    game_ids = {g.game_id for g in games if g.game_id is not None}
    igdb_games_dict = {}
    if game_ids:
        igdb_games_query = await db.execute(
            select(IgdbGame).where(IgdbGame.id.in_(game_ids))
        )
        igdb_games = igdb_games_query.scalars().all()
        igdb_games_dict = {game.id: game for game in igdb_games}

    users_models = []
    for user in users:
        model = UserSummary.model_validate(user)
        model.games = [
            UserGame(
                sector_id=g.sector_id,
                title=g.item_title,
                length=g.item_length,
                created_at=g.created_at,
                status=cast(GameCompletionType, g.type),
                review=g.item_review,
                rating=g.item_rating,
                duration_seconds=g.duration,
                vod_links=g.vod_links,
                cover=igdb_games_dict[g.game_id].cover
                if g.game_id and g.game_id in igdb_games_dict
                else None,
            )
            for g in games
            if g.player_id == user.id
        ]
        model.games.sort(key=lambda x: x.created_at, reverse=True)

        model.bonus_cards = [
            BonusCard(
                bonus_type=c.card_type,
                received_at=c.created_at,
                received_on_sector=c.received_on_sector,
            )
            for c in cards
            if c.player_id == user.id
        ]

        model.current_game_duration_seconds = await get_current_game_duration(db, user.id, user.current_game)

        users_models.append(model)
    return {"players": users_models}


@app.get("/api/players/{player_id}/events", response_model=EventsList)
async def get_player_events(
    player_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    moves_query = await db.execute(
        select(PlayerMove).where(PlayerMove.player_id == player_id)
    )
    moves = moves_query.scalars().all()
    move_events = [
        MoveEvent(
            subtype=PlayerMoveType(e.move_type),
            sector_from=e.sector_from,
            sector_to=e.sector_to,
            map_completed=bool(e.map_completed),
            adjusted_roll=e.adjusted_roll,
            dice_roll=[],
            timestamp=e.created_at,
        )
        for e in moves
    ]

    games_query = await db.execute(
        select(PlayerGame).where(PlayerGame.player_id == player_id)
    )
    games = games_query.scalars().all()
    game_events = [
        GameEvent(
            subtype=GameCompletionType(e.type),
            game_title=e.item_title,
            sector_id=e.sector_id,
            timestamp=e.created_at,
        )
        for e in games
    ]

    cards_query = await db.execute(
        select(PlayerCard).where(PlayerCard.player_id == player_id)
    )
    cards = cards_query.scalars().all()
    bonus_card_events = [
        BonusCardEvent(
            subtype=map_bonus_card_to_event_type(e),
            bonus_type=MainBonusCardType(e.card_type),
            sector_id=e.received_on_sector,
            timestamp=e.created_at,
            used_at=e.used_at,
            used_on_sector=e.used_on_sector,
            lost_at=e.lost_at,
            lost_on_sector=e.lost_on_sector,
            stolen_at=e.stolen_at,
            stolen_from_player=e.stolen_from_player,
            stolen_by=e.stolen_by,
        )
        for e in cards
    ]

    scores_query = await db.execute(
        select(PlayerScoreChange).where(PlayerScoreChange.player_id == player_id)
    )
    score_changes = scores_query.scalars().all()
    score_change_events = [
        ScoreChangeEvent(
            subtype=ScoreChangeType(e.change_type),
            amount=e.score_change,
            reason=e.description,
            sector_id=e.sector_id,
            timestamp=e.created_at,
        )
        for e in score_changes
    ]
    all_events = move_events + game_events + bonus_card_events + score_change_events
    return {"events": all_events}


@app.post("/api/players/current/moves")
async def do_player_move(
    move: MakePlayerMove,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    roll_result = move.tmp_roll_result
    sector_to = current_user.sector_id + roll_result
    map_completed = False
    if sector_to > 40:
        sector_to = sector_to % 40
        map_completed = True

    move_item = PlayerMove(
        player_id=current_user.id,
        sector_from=current_user.sector_id,
        sector_to=sector_to,
        move_type=move.type.value,
        map_completed=map_completed,
        adjusted_roll=roll_result,
        random_org_roll=0,
    )
    db.add(move_item)
    current_user.sector_id = sector_to
    if map_completed:
        current_user.maps_completed += 1

    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        duration_result = await calculate_time_by_category_name(db, request.title, current_user.id)
        game_duration = int(duration_result.get("total_difference_in_seconds", 0) or 0)
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

    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/rules/current", response_model=RulesResponse)
async def get_current_rules_version(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rules_query = await db.execute(select(Rules).order_by(Rules.created_at.desc()))
    rules = rules_query.scalars().first()
    if not rules:
        return {
            "versions": [
                {
                    "content": json.dumps(
                        {"ops": [{"insert": "Пока ничего не добавили"}]}
                    ),
                    "created_at": round(datetime.now().timestamp()),
                }
            ]
        }
    return {"versions": [rules]}


@app.get("/api/rules", response_model=RulesResponse)
async def get_all_rules_versions(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rules_query = await db.execute(select(Rules).order_by(Rules.created_at.desc()))
    rules = rules_query.scalars().all()
    return {"versions": rules}


@app.post("/api/rules")
async def create_new_rules_version(
    request: RulesVersion,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # if current_user.username.lower() != "praden":
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
    #     )

    new_rule = Rules(content=request.content)
    db.add(new_rule)
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
    search_query = (
        select(IgdbGame).where(IgdbGame.name.ilike(f"%{query}%")).limit(limit)
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
                detail={
                    "success": False,
                    "stats": stats
                }
            )
        
        return StreamCheckResponse(
            success=True,
            stats=stats
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "stats": {}
            }
        )