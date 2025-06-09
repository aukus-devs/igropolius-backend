from typing import Annotated

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.params import Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import (
    CurrentUser,
    EventsList,
    LoginRequest,
    MakePlayerMove,
    SavePlayerGame,
    UpdatePlayerTurnState,
    UserGame,
    UserSummary,
    UsersList,
)
from src.db import get_db
from src.db_models import PlayerGame, PlayerMove, PlayerScoreChange, User
from src.utils.auth import get_current_user
from src.utils.common import safe_commit
from src.utils.jwt import create_access_token, verify_password

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

    users_models = []
    for user in users:
        model = UserSummary.model_validate(user)
        model.games = [
            UserGame(
                sector_id=g.sector_id,
                game_title=g.item_title,
                game_length=g.item_length,
                created_at=g.created_at,
            )
            for g in games
            if g.player_id == user.id
        ]
        users_models.append(model)
    return {"players": users_models}


@app.get("/api/players/{player_id}/events", response_model=EventsList)
async def get_player_events(
    player_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return {"events": []}


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
    game = PlayerGame(
        player_id=current_user.id,
        type=request.status.value,
        item_title=request.title,
        item_review=request.review,
        item_rating=request.rating,
        item_length=request.length,
        vod_links=request.vod_links,
        sector_id=current_user.sector_id,
    )
    db.add(game)

    score_change = PlayerScoreChange(
        player_id=current_user.id,
        score_change=request.scores,
        reason="Game completed",
        sector_id=current_user.sector_id,
    )
    db.add(score_change)

    current_user.total_score += request.scores

    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
