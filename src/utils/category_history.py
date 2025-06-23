import re
from typing import Optional, Dict, Any
from sqlalchemy import select, text, func, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.db_models import CategoryHistory
from src.utils.db import utc_now_ts
from src.config import SAVE_STREAM_CATEGORIES


async def delete_old_category_records(
    db: AsyncSession, player_id: int, category_name: str
) -> None:
    query = delete(CategoryHistory).where(
        CategoryHistory.player_id == player_id,
        CategoryHistory.category_name == category_name,
    )

    await db.execute(query)


async def save_category_history(
    db: AsyncSession, player_id: int, category_name: str
) -> None:
    if not SAVE_STREAM_CATEGORIES:
        return

    if category_name.lower() in ["just chatting", "говорим и смотрим"]:
        await delete_old_category_records(db, player_id, category_name)

    category_history = CategoryHistory(
        category_name=category_name, player_id=player_id, category_date=utc_now_ts()
    )

    db.add(category_history)


async def find_category_by_prefix(
    db: AsyncSession, player_id: int, prefix: str, limit: int = 1
) -> Optional[str]:
    query = (
        select(CategoryHistory.category_name)
        .where(
            CategoryHistory.player_id == player_id,
            CategoryHistory.category_name.ilike(f"{prefix}%"),
        )
        .order_by(desc(CategoryHistory.category_date))
        .limit(limit)
    )

    result = await db.execute(query)
    return result.scalars().first()


async def calculate_time_by_category_name(
    db: AsyncSession, category_name: str, player_id: int
) -> Dict[str, Any]:
    clean_category_name = re.sub(r"\(.*?\)", "", category_name.strip())

    query = text("""
        WITH time_differences AS (
            SELECT
                category_name,
                player_id,
                category_date,
                LEAD(category_name) OVER (PARTITION BY player_id ORDER BY id) AS next_category_name,
                LEAD(category_date) OVER (PARTITION BY player_id ORDER BY id) AS next_category_date
            FROM
                categories_history
        )
        SELECT
            category_name,
            SUM(
                CASE
                    WHEN next_category_name IS NULL THEN
                        (:current_time - category_date)
                    WHEN next_category_name != category_name THEN
                        (next_category_date - category_date)
                    ELSE
                        0
                END
            ) AS total_difference_in_seconds
        FROM
            time_differences
        WHERE
            category_name = :category_name AND
            player_id = :player_id
        GROUP BY
            category_name;
    """)

    result = await db.execute(
        query,
        {
            "category_name": clean_category_name,
            "player_id": player_id,
            "current_time": utc_now_ts(),
        },
    )

    row = result.first()

    if row is None:
        return {"total_difference_in_seconds": 0}
    else:
        return {"total_difference_in_seconds": row.total_difference_in_seconds or 0}


async def get_player_categories_stats(
    db: AsyncSession, player_id: int
) -> Dict[str, int]:
    query = (
        select(CategoryHistory.category_name, func.count().label("count"))
        .where(CategoryHistory.player_id == player_id)
        .group_by(CategoryHistory.category_name)
        .order_by(func.count().desc())
    )

    result = await db.execute(query)
    rows = result.all()

    return {row.category_name: row.count for row in rows}


async def get_current_game_duration(
    db: AsyncSession, player_id: int, current_game: Optional[str]
) -> Optional[int]:
    if not current_game:
        return None

    result = await calculate_time_by_category_name(db, current_game, player_id)
    total_seconds = result.get("total_difference_in_seconds", 0)

    if total_seconds <= 0:
        return None

    return int(total_seconds)


async def calculate_game_duration_by_title(
    db: AsyncSession, game_title: str, player_id: int
) -> int:
    clean_game_title = re.sub(r"\s*\(\d{4}\)", "", game_title).strip()

    found_category = await find_category_by_prefix(db, player_id, clean_game_title)

    if not found_category:
        return 0

    result = await calculate_time_by_category_name(db, found_category, player_id)
    return int(result.get("total_difference_in_seconds", 0) or 0)
