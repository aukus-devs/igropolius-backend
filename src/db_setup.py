import asyncio

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import get_session, init_db_async
from src.db_models import User, IgdbGame
from src.enums import PlayerTurnState, StreamPlatform
from src.utils.jwt import hash_password


class UserData(BaseModel):
    username: str
    first_name: str
    main_platform: StreamPlatform = StreamPlatform.NONE
    twitch_stream_link: str | None = None
    vk_stream_link: str | None = None
    kick_stream_link: str | None = None
    telegram_link: str | None = None
    donation_link: str | None = None
    is_active: int = 1


class GameData(BaseModel):
    name: str
    cover: str | None = None
    release_year: int | None = None


defined_users = [
    UserData(
        username="Praden",
        first_name="Денис",
        main_platform=StreamPlatform.TWITCH,
        twitch_stream_link="https://www.twitch.tv/praden",
        vk_stream_link="https://live.vkvideo.ru/praden",
        kick_stream_link="https://kick.com/praden",
        telegram_link="https://t.me/praden",
        donation_link="https://praden.donationalerts.com/",
    ),
    UserData(
        username="Player-2",
        first_name="Player2",
        main_platform=StreamPlatform.VK,
        vk_stream_link="https://live.vkvideo.ru/radiorecord",
    ),
    UserData(
        username="Player-3",
        first_name="Player3",
        main_platform=StreamPlatform.KICK,
        kick_stream_link="https://kick.com/mitisx-live",
    ),
    UserData(username="Player-4", first_name="Player4"),
    UserData(username="Player-5", first_name="Player5"),
    UserData(username="Player-6", first_name="Player6"),
    UserData(username="Player-7", first_name="Player7"),
    UserData(username="Player-8", first_name="Player8"),
]

defined_games = [
    GameData(
        name="The Witcher 3: Wild Hunt",
        cover="https://images.igdb.com/igdb/image/upload/t_cover_big/co1wyy.webp",
        release_year=2015,
    ),
    GameData(
        name="Cyberpunk 2077",
        cover="https://images.igdb.com/igdb/image/upload/t_cover_big/co7497.webp",
        release_year=2020,
    ),
    GameData(
        name="Red Dead Redemption 2",
        cover="https://images.igdb.com/igdb/image/upload/t_cover_big/co1q1f.webp",
        release_year=2018,
    ),
    GameData(
        name="Grand Theft Auto V",
        cover="https://images.igdb.com/igdb/image/upload/t_cover_big/co2lbd.webp",
        release_year=2013,
    ),
    GameData(
        name="Dark Souls III",
        cover="https://images.igdb.com/igdb/image/upload/t_cover_big/co1vcf.webp",
        release_year=2016,
    ),
    GameData(name="The Wolf Among Us", cover=None, release_year=2013),
    GameData(name="Among Us", cover=None, release_year=2018),
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
        main_platform=user_data.main_platform.value,
        twitch_stream_link=user_data.twitch_stream_link,
        vk_stream_link=user_data.vk_stream_link,
        kick_stream_link=user_data.kick_stream_link,
        telegram_link=user_data.telegram_link,
        donation_link=user_data.donation_link,
        is_active=user_data.is_active,
        sector_id=1,
        total_score=0.0,
        turn_state=PlayerTurnState.ROLLING_DICE.value,
        maps_completed=0,
    )


def create_user(db: AsyncSession, user_data: UserData):
    user = make_user(user_data)
    db.add(user)


def make_game(game_data: GameData):
    return IgdbGame(
        name=game_data.name,
        cover=game_data.cover,
        release_year=game_data.release_year,
    )


def create_game(db: AsyncSession, game_data: GameData):
    game = make_game(game_data)
    db.add(game)


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


async def create_games():
    async with get_session() as db:
        count_query = await db.execute(select(IgdbGame.id))
        existing_games = count_query.scalars().all()

        if len(existing_games) == 0:
            for game_data in defined_games:
                create_game(db, game_data)
            await db.commit()


async def main():
    await init_db_async()
    print("Database initialized successfully.")

    await create_users()
    print("Test users created successfully.")

    await create_games()
    print("Test games created successfully.")


if __name__ == "__main__":
    asyncio.run(main())
