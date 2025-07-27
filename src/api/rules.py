from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import RulesResponse, NewRulesVersionRequest
from src.db.db_session import get_db
from src.db.db_models import Rules, User
from src.enums import Role
from src.utils.auth import get_current_user


router = APIRouter(tags=["rules"])


@router.get("/api/rules/current", response_model=RulesResponse)
async def get_current_rules_version(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    subquery = (
        select(Rules.category, func.max(Rules.id).label("latest_id"))
        .group_by(Rules.category)
        .subquery()
    )

    rules_query = await db.execute(
        select(Rules)
        .join(subquery, Rules.category == subquery.c.category)
        .where(Rules.id == subquery.c.latest_id)
    )

    rules = rules_query.scalars().all()
    return {"versions": rules}


@router.get("/api/rules", response_model=RulesResponse)
async def get_all_rules_versions(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rules_query = await db.execute(select(Rules).order_by(Rules.created_at.desc()))
    rules = rules_query.scalars().all()
    return {"versions": rules}


@router.post("/api/rules")
async def create_new_rules_version(
    request: NewRulesVersionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.role != Role.ADMIN.value:
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    new_rule = Rules(content=request.content, category=request.category.value)
    db.add(new_rule)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
