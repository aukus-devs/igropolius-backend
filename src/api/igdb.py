from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import IgdbGamesList
from src.db import get_db
from src.db_models import IgdbGame, User
from src.utils.auth import get_current_user


router = APIRouter(tags=["igdb"])


@router.get("/api/igdb/games/{game_id}")
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


@router.get("/api/igdb/games/search", response_model=IgdbGamesList)
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
