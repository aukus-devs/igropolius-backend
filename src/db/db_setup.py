import asyncio

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.db_models import EventSettings, HltbGame, IgdbGame, User
from src.enums import PlayerTurnState, Role, StreamPlatform
from src.utils.jwt import hash_password

from .db_session import get_session, init_db_async


class UserData(BaseModel):
    username: str
    first_name: str
    role: Role = Role.PLAYER
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


class HltbGameData(BaseModel):
    game_id: int
    game_name: str
    game_name_date: int
    game_alias: str | None = None
    game_type: str
    game_image: str
    comp_lvl_combine: int
    comp_lvl_sp: int
    comp_lvl_co: int
    comp_lvl_mp: int
    comp_main: int
    comp_plus: int
    comp_100: int
    comp_all: int
    comp_main_count: int
    comp_plus_count: int
    comp_100_count: int
    comp_all_count: int
    invested_co: int
    invested_mp: int
    invested_co_count: int
    invested_mp_count: int
    count_comp: int
    count_speedrun: int
    count_backlog: int
    count_review: int
    review_score: int
    count_playing: int
    count_retired: int
    profile_platform: str | None = None
    profile_popular: int
    release_world: int
    created_at: int
    updated_at: int


defined_users = [
    UserData(
        username="Praden",
        first_name="Денис",
        role=Role.ADMIN,
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

defined_hltb_games = [
    HltbGameData(
        game_id=18,
        game_name="'Splosion Man",
        game_name_date=0,
        game_alias=None,
        game_type="game",
        game_image="18_Splosion_Man.png",
        comp_lvl_combine=0,
        comp_lvl_sp=1,
        comp_lvl_co=1,
        comp_lvl_mp=1,
        comp_main=28088,
        comp_plus=34622,
        comp_100=63446,
        comp_all=31462,
        comp_main_count=32,
        comp_plus_count=21,
        comp_100_count=7,
        comp_all_count=60,
        invested_co=32400,
        invested_mp=0,
        invested_co_count=1,
        invested_mp_count=0,
        count_comp=186,
        count_speedrun=0,
        count_backlog=305,
        count_review=83,
        review_score=73,
        count_playing=0,
        count_retired=44,
        profile_platform="Xbox 360",
        profile_popular=24,
        release_world=2009,
        created_at=1723852800,
        updated_at=1723852800,
    ),
    HltbGameData(
        game_id=19,
        game_name=".hack//G.U. Vol. 1: Rebirth",
        game_name_date=0,
        game_alias=None,
        game_type="game",
        game_image="Cover-dothackGU.jpg",
        comp_lvl_combine=0,
        comp_lvl_sp=1,
        comp_lvl_co=1,
        comp_lvl_mp=1,
        comp_main=66913,
        comp_plus=86087,
        comp_100=131511,
        comp_all=84563,
        comp_main_count=75,
        comp_plus_count=78,
        comp_100_count=25,
        comp_all_count=178,
        invested_co=0,
        invested_mp=0,
        invested_co_count=0,
        invested_mp_count=0,
        count_comp=290,
        count_speedrun=2,
        count_backlog=324,
        count_review=116,
        review_score=75,
        count_playing=3,
        count_retired=20,
        profile_platform="Nintendo Switch, PC, PlayStation 2, PlayStation 4",
        profile_popular=15,
        release_world=2006,
        created_at=1723852800,
        updated_at=1723852800,
    ),
    HltbGameData(
        game_id=20,
        game_name=".hack//G.U. Vol. 2: Reminisce",
        game_name_date=0,
        game_alias=None,
        game_type="game",
        game_image="51PU4XWwg-L.jpg",
        comp_lvl_combine=0,
        comp_lvl_sp=1,
        comp_lvl_co=1,
        comp_lvl_mp=1,
        comp_main=71370,
        comp_plus=107289,
        comp_100=166960,
        comp_all=95822,
        comp_main_count=41,
        comp_plus_count=31,
        comp_100_count=16,
        comp_all_count=88,
        invested_co=0,
        invested_mp=0,
        invested_co_count=0,
        invested_mp_count=0,
        count_comp=176,
        count_speedrun=0,
        count_backlog=301,
        count_review=72,
        review_score=78,
        count_playing=3,
        count_retired=8,
        profile_platform="Nintendo Switch, PC, PlayStation 2, PlayStation 4",
        profile_popular=15,
        release_world=2006,
        created_at=1723852800,
        updated_at=1723852800,
    ),
    HltbGameData(
        game_id=21,
        game_name=".hack//G.U. Vol. 3: Redemption",
        game_name_date=0,
        game_alias=None,
        game_type="game",
        game_image="51C9Z2aYvwL.jpg",
        comp_lvl_combine=0,
        comp_lvl_sp=1,
        comp_lvl_co=1,
        comp_lvl_mp=1,
        comp_main=75792,
        comp_plus=109537,
        comp_100=170207,
        comp_all=97005,
        comp_main_count=34,
        comp_plus_count=27,
        comp_100_count=8,
        comp_all_count=69,
        invested_co=0,
        invested_mp=0,
        invested_co_count=0,
        invested_mp_count=0,
        count_comp=142,
        count_speedrun=0,
        count_backlog=302,
        count_review=63,
        review_score=77,
        count_playing=2,
        count_retired=7,
        profile_platform="Nintendo Switch, PC, PlayStation 2, PlayStation 4",
        profile_popular=12,
        release_world=2007,
        created_at=1723852800,
        updated_at=1723852800,
    ),
]


def make_user(user_data: UserData):
    password = "pass"
    hashed = hash_password(password)
    return User(
        username=user_data.username,
        password_hash=hashed,
        first_name=user_data.first_name,
        url_handle=user_data.username.lower(),
        role=user_data.role.value,
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


def make_hltb_game(hltb_game_data: HltbGameData):
    return HltbGame(
        game_id=hltb_game_data.game_id,
        game_name=hltb_game_data.game_name,
        game_name_date=hltb_game_data.game_name_date,
        game_alias=hltb_game_data.game_alias,
        game_type=hltb_game_data.game_type,
        game_image=hltb_game_data.game_image,
        comp_lvl_combine=hltb_game_data.comp_lvl_combine,
        comp_lvl_sp=hltb_game_data.comp_lvl_sp,
        comp_lvl_co=hltb_game_data.comp_lvl_co,
        comp_lvl_mp=hltb_game_data.comp_lvl_mp,
        comp_main=hltb_game_data.comp_main,
        comp_plus=hltb_game_data.comp_plus,
        comp_100=hltb_game_data.comp_100,
        comp_all=hltb_game_data.comp_all,
        comp_main_count=hltb_game_data.comp_main_count,
        comp_plus_count=hltb_game_data.comp_plus_count,
        comp_100_count=hltb_game_data.comp_100_count,
        comp_all_count=hltb_game_data.comp_all_count,
        invested_co=hltb_game_data.invested_co,
        invested_mp=hltb_game_data.invested_mp,
        invested_co_count=hltb_game_data.invested_co_count,
        invested_mp_count=hltb_game_data.invested_mp_count,
        count_comp=hltb_game_data.count_comp,
        count_speedrun=hltb_game_data.count_speedrun,
        count_backlog=hltb_game_data.count_backlog,
        count_review=hltb_game_data.count_review,
        review_score=hltb_game_data.review_score,
        count_playing=hltb_game_data.count_playing,
        count_retired=hltb_game_data.count_retired,
        profile_platform=hltb_game_data.profile_platform,
        profile_popular=hltb_game_data.profile_popular,
        release_world=hltb_game_data.release_world,
        created_at=hltb_game_data.created_at,
        updated_at=hltb_game_data.updated_at,
    )


def create_hltb_game(db: AsyncSession, hltb_game_data: HltbGameData):
    hltb_game = make_hltb_game(hltb_game_data)
    db.add(hltb_game)


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


async def create_hltb_games():
    async with get_session() as db:
        count_query = await db.execute(select(HltbGame.game_id))
        existing_hltb_games = count_query.scalars().all()

        if len(existing_hltb_games) == 0:
            for hltb_game_data in defined_hltb_games:
                create_hltb_game(db, hltb_game_data)
            await db.commit()


async def create_event_settings():
    async with get_session() as db:
        existing_settings_query = await db.execute(select(EventSettings.key_name))
        existing_keys = set(existing_settings_query.scalars().all())

        default_settings = {
            "event_start_time": "1",
            "event_end_time": "2",
            "endpoint_reset_db_enabled": "0",
        }

        for key, value in default_settings.items():
            if key not in existing_keys:
                setting = EventSettings(key_name=key, value=value)
                db.add(setting)

        await db.commit()


async def main():
    await init_db_async()
    print("Database initialized successfully.")

    await create_users()
    print("Test users created successfully.")

    await create_games()
    print("Test games created successfully.")

    await create_hltb_games()
    print("Test HLTB games created successfully.")

    await create_event_settings()
    print("Event settings initialized successfully.")


if __name__ == "__main__":
    asyncio.run(main())
