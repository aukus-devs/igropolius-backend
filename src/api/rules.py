import json
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import RulesResponse, RulesVersion
from src.db import get_db
from src.db_models import Rules, User
from src.utils.auth import get_current_user
from src.utils.db import safe_commit, utc_now_ts


router = APIRouter(tags=["rules"])


@router.get("/api/rules/current", response_model=RulesResponse)
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
                    "created_at": utc_now_ts(),
                }
            ]
        }
    return {"versions": [rules]}


@router.get("/api/rules", response_model=RulesResponse)
async def get_all_rules_versions(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rules_query = await db.execute(select(Rules).order_by(Rules.created_at.desc()))
    rules = rules_query.scalars().all()
    return {"versions": rules}


@router.post("/api/rules")
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
