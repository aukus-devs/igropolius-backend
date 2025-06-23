import json
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api_models import RollDiceRequest, RollDiceResponse
from src.db import get_db
from src.db_models import DiceRoll, User
from src.utils.auth import get_current_user
from src.utils.db import safe_commit
from src.utils.random_org import get_random_numbers


router = APIRouter(tags=["dice"])


@router.post("/api/dice/roll", response_model=RollDiceResponse)
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
