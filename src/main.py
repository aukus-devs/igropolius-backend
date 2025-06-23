from typing import Annotated
import json

from fastapi import FastAPI, HTTPException, status
from fastapi.params import Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import (
    RollDiceRequest,
    RollDiceResponse,
    StreamCheckResponse,
)
from src.db import get_db
from src.db_models import (
    User,
    DiceRoll,
)
from src.utils.auth import get_current_user
from src.utils.db import safe_commit
from src.utils.random_org import get_random_numbers
from src.api import auth, players, rules, bonus_cards, taxes, igdb

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
app.include_router(bonus_cards.router)
app.include_router(taxes.router)
app.include_router(igdb.router)


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
