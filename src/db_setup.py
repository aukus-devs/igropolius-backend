import asyncio

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import get_session, init_db_async
from src.db_models import User
from src.enums import PlayerTurnState
from src.utils.jwt import hash_password


class UserData(BaseModel):
    username: str
    first_name: str
    twitch_stream_link: str | None = None
    vk_stream_link: str | None = None
    kick_stream_link: str | None = None
    telegram_link: str | None = None
    donation_link: str | None = None
    is_active: int = 1


defined_users = [
    UserData(
        username="Praden",
        first_name="Денис",
        twitch_stream_link="https://www.twitch.tv/praden",
        vk_stream_link="https://live.vkvideo.ru/praden",
        kick_stream_link="https://kick.com/praden",
        telegram_link="https://t.me/praden",
        donation_link="https://praden.donationalerts.com/",
    ),
    UserData(username="Player-2", first_name="Player2"),
    UserData(username="Player-3", first_name="Player3"),
    UserData(username="Player-4", first_name="Player4"),
    UserData(username="Player-5", first_name="Player5"),
    UserData(username="Player-6", first_name="Player6"),
    UserData(username="Player-7", first_name="Player7"),
    UserData(username="Player-8", first_name="Player8"),
]


def make_user(user_data: UserData):
    password = "pass"
    hashed = hash_password(password)
    return User(
        username=user_data.username,
        password_hash=hashed,
        first_name=user_data.first_name,
        url_handle=user_data.username.lower(),
        is_online=0,
        current_game=None,
        current_game_updated_at=None,
        online_count=0,
        current_auc_total_sum=None,
        current_auc_started_at=None,
        pointauc_token=None,
        twitch_stream_link=user_data.twitch_stream_link,
        vk_stream_link=user_data.vk_stream_link,
        kick_stream_link=user_data.kick_stream_link,
        telegram_link=user_data.telegram_link,
        donation_link=user_data.donation_link,
        is_active=user_data.is_active,
        sector_id=1,
        total_score=0.0,
        turn_state=PlayerTurnState.ROLLING_DICE.value,
        last_dice_roll_id=None,
        maps_completed=0,
    )


def create_user(db: AsyncSession, user_data: UserData):
    user = make_user(user_data)
    db.add(user)


def user_to_dict(obj: User):
    return {
        c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name != "id"
    }


async def update_user(db: AsyncSession, user_data: UserData):
    user = make_user(user_data)
    await db.execute(
        update(User)
        .where(User.username == user_data.username)
        .values(**user_to_dict(user))
    )


async def create_users():
    async with get_session() as db:
        query = await db.execute(select(User.username))
        usernames = set(query.scalars().all())
        for user_data in defined_users:
            if user_data.username not in usernames:
                create_user(db, user_data)
            else:
                await update_user(db, user_data)
        await db.commit()


async def main():
    await init_db_async()
    print("Database initialized successfully.")

    await create_users()
    print("Test users created successfully.")


if __name__ == "__main__":
    asyncio.run(main())
