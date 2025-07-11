from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.db_models import User


async def get_players_by_score(
    db: AsyncSession, *, for_update: bool = False
) -> list[User]:
    query = select(User).where(User.is_active == True).order_by(User.total_score.desc())
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    players = result.scalars().all()
    return players
