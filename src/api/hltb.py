from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import (
    HltbGameResponse,
    HltbGamesListResponse,
    HltbRandomGameRequest,
)
from src.db.db_models import HltbGame
from src.db.db_session import get_db

router = APIRouter(tags=["hltb"])


@router.post("/api/hltb/random-game", response_model=HltbGamesListResponse)
async def get_random_game(
    db: Annotated[AsyncSession, Depends(get_db)],
    request: HltbRandomGameRequest = Body(...),
):
    if request.min_length is not None and request.max_length is not None:
        min_length_seconds = request.min_length * 3600
        max_length_seconds = request.max_length * 3600

        query = (
            select(HltbGame)
            .where(
                and_(
                    HltbGame.profile_platform.like("%PC%"),
                    HltbGame.game_type == "game",
                    or_(
                        and_(
                            HltbGame.comp_main > 0,
                            HltbGame.comp_main >= min_length_seconds,
                            HltbGame.comp_main <= max_length_seconds,
                        ),
                        and_(
                            HltbGame.comp_main == 0,
                            HltbGame.comp_plus > 0,
                            HltbGame.comp_plus >= min_length_seconds,
                            HltbGame.comp_plus <= max_length_seconds,
                        ),
                        and_(
                            HltbGame.comp_main == 0,
                            HltbGame.comp_plus == 0,
                            HltbGame.comp_100 > 0,
                            HltbGame.comp_100 >= min_length_seconds,
                            HltbGame.comp_100 <= max_length_seconds,
                        ),
                        and_(
                            HltbGame.comp_main == 0,
                            HltbGame.comp_plus == 0,
                            HltbGame.comp_100 == 0,
                            HltbGame.comp_all > 0,
                            HltbGame.comp_all >= min_length_seconds,
                            HltbGame.comp_all <= max_length_seconds,
                        ),
                    ),
                )
            )
            .order_by(func.random())
            .limit(request.limit)
        )
    else:
        query = (
            select(HltbGame)
            .where(
                and_(
                    HltbGame.profile_platform.like("%PC%"),
                    HltbGame.game_type == "game",
                )
            )
            .order_by(func.random())
            .limit(request.limit)
        )

    result = await db.execute(query)
    games = result.scalars().all()

    if not games:
        raise HTTPException(
            status_code=404, detail="No games found with specified criteria"
        )

    games_response = []
    for game in games:
        game_response = HltbGameResponse(
            game_id=game.game_id,
            game_name=game.game_name,
            game_name_date=game.game_name_date,
            game_alias=game.game_alias,
            game_type=game.game_type,
            game_image=f"https://howlongtobeat.com/games/{game.game_image}",
            comp_lvl_combine=game.comp_lvl_combine,
            comp_lvl_sp=game.comp_lvl_sp,
            comp_lvl_co=game.comp_lvl_co,
            comp_lvl_mp=game.comp_lvl_mp,
            comp_main=game.comp_main,
            comp_plus=game.comp_plus,
            comp_100=game.comp_100,
            comp_all=game.comp_all,
            comp_main_count=game.comp_main_count,
            comp_plus_count=game.comp_plus_count,
            comp_100_count=game.comp_100_count,
            comp_all_count=game.comp_all_count,
            invested_co=game.invested_co,
            invested_mp=game.invested_mp,
            invested_co_count=game.invested_co_count,
            invested_mp_count=game.invested_mp_count,
            count_comp=game.count_comp,
            count_speedrun=game.count_speedrun,
            count_backlog=game.count_backlog,
            count_review=game.count_review,
            review_score=game.review_score,
            count_playing=game.count_playing,
            count_retired=game.count_retired,
            profile_platform=game.profile_platform,
            profile_popular=game.profile_popular,
            release_world=game.release_world,
            created_at=game.created_at,
            updated_at=game.updated_at,
        )
        games_response.append(game_response)

    return HltbGamesListResponse(games=games_response)
