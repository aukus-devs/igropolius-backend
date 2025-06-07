import asyncio

from sqlalchemy import func, select
from src.db import get_session, init_db_async
from src.db_models import User
from src.enums import PlayerTurnState
from src.utils.jwt import hash_password


def create_test_user(db, id: int):
    password = "pass"
    hashed = hash_password(password)
    db.add(
        User(
            username=f"user_{id}",
            password_hash=hashed,
            first_name=f"User_{id}",
            url_handle=f"user{id}",
            is_online=0,
            current_game=None,
            current_game_updated_at=None,
            online_count=0,
            current_auc_total_sum=None,
            current_auc_started_at=None,
            pointauc_token=None,
            twitch_stream_link=None,
            vk_stream_link=None,
            kick_stream_link=None,
            telegram_link=None,
            donation_link=None,
            is_active=1,
            sector_id=1,
            total_score=0.0,
            turn_state=PlayerTurnState.INITIAL.value,
            last_dice_roll_id=None,
            maps_completed=0,
        )
    )


async def create_users():
    async with get_session() as db:
        query = await db.execute(select(func.count()).select_from(User))
        users_count = query.scalar_one()
        if users_count == 0:
            for i in range(1, 9):
                create_test_user(db, i)
            await db.commit()


if __name__ == "__main__":
    asyncio.run(init_db_async())
    print("Database initialized successfully.")

    asyncio.run(create_users())
    print("Test users created successfully.")
