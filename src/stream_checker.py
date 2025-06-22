import requests
from lxml import html
import os
import logging
from typing import Dict, Any
import cloudscraper
import ua_generator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db_models import User, PlayerGame, IgdbGame
from src.utils.db import safe_commit, utc_now_ts
from src.utils.category_history import save_category_history
from src.enums import StreamPlatform

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

twitch_headers = {
    "Client-ID": os.getenv("TWITCH_CLIENT_ID"),
    "Authorization": os.getenv("TWITCH_BEARER_TOKEN"),
}

kick_session = cloudscraper.CloudScraper()
kick_ua = ua_generator.generate()
kick_headers = {
    "Accept": "application/json",
    "Alt-Used": "kick.com",
    "Priority": "u=0, i",
    "Connection": "keep-alive",
    "User-Agent": kick_ua.text,
}


async def _player_has_completed_game(
    db: AsyncSession, player_id: int, game_name: str
) -> bool:
    query = await db.execute(
        select(PlayerGame)
        .where(PlayerGame.player_id == player_id)
        .where(PlayerGame.item_title == game_name)
        .limit(1)
    )

    existing_game = query.scalars().first()
    return existing_game is not None


async def _get_game_cover(db: AsyncSession, game_name: str) -> str | None:
    from sqlalchemy import case

    query = await db.execute(
        select(IgdbGame.cover)
        .where(IgdbGame.name.ilike(f"{game_name}%"))
        .order_by(
            case((IgdbGame.name.ilike(f"{game_name}%"), 0), else_=1), IgdbGame.name
        )
        .limit(1)
    )

    result = query.scalar_one_or_none()
    return result


def _get_twitch_user_avatar(username: str) -> str | None:
    try:
        url = f"https://api.twitch.tv/helix/users?login={username}"
        response = requests.get(url, headers=twitch_headers, timeout=15)
        response.raise_for_status()

        data = response.json()["data"]
        if len(data) > 0:
            return data[0]["profile_image_url"]
    except Exception as e:
        logger.error(f"Error getting Twitch avatar for {username}: {str(e)}")

    return None


def _get_vk_user_avatar(stream_link: str) -> str | None:
    try:
        response = requests.get(stream_link, timeout=15)
        response.raise_for_status()

        content = html.fromstring(response.content)

        avatar_xpath = content.xpath(
            "/html/body/div[1]/div/div[2]/div[2]/div/div[3]/div[1]/div[1]/div/div[1]/div[1]/div[1]/div/img/@src"
        )

        if len(avatar_xpath) > 0:
            avatar_url = avatar_xpath[0]
            if avatar_url.startswith("//"):
                avatar_url = "https:" + avatar_url
            elif avatar_url.startswith("/"):
                avatar_url = "https://vkplay.live" + avatar_url
            return avatar_url
    except Exception as e:
        logger.error(f"Error getting VK avatar from {stream_link}: {str(e)}")

    return None


def _get_kick_channel_data(username: str) -> dict | None:
    try:
        url = f"https://kick.com/api/v1/channels/{username}"
        response = kick_session.get(url, headers=kick_headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting Kick data for {username}: {str(e)}")

    return None


async def refresh_stream_statuses(db: AsyncSession) -> Dict[str, Any]:
    stats: Dict[str, Any] = {
        "total_players": 0,
        "updated_players": 0,
        "online_players": 0,
        "errors": [],
    }

    try:
        query = await db.execute(select(User).filter(User.is_active == 1))
        players = query.scalars().all()
        stats["total_players"] = len(players)

        for player in players:
            try:
                updated = await _check_single_player_stream(player, db)
                if updated:
                    stats["updated_players"] += 1
                if player.is_online:
                    stats["online_players"] += 1

            except Exception as e:
                error_msg = f"Error checking stream for {player.username}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        await safe_commit(db)

    except Exception as e:
        error_msg = f"General error checking streams: {str(e)}"
        logger.error(error_msg)
        stats["errors"].append(error_msg)

    return stats


async def _check_single_player_stream(player: User, db: AsyncSession) -> bool:
    updated = False

    if (
        player.main_platform == StreamPlatform.TWITCH.value
        and player.twitch_stream_link
    ):
        updated = await _check_twitch_stream(player, db)
    elif player.main_platform == StreamPlatform.VK.value and player.vk_stream_link:
        updated = await _check_vk_stream(player, db)
    elif player.main_platform == StreamPlatform.KICK.value and player.kick_stream_link:
        updated = await _check_kick_stream(player, db)

    return updated


async def _check_twitch_stream(player: User, db: AsyncSession) -> bool:
    try:
        username = player.twitch_stream_link.rsplit("/", 1)[1]
        url = f"https://api.twitch.tv/helix/streams?user_login={username}"

        response = requests.get(url, headers=twitch_headers, timeout=15)
        response.raise_for_status()

        data = response.json()["data"]

        if len(data) != 0 and data[0]["type"] == "live":
            stream = data[0]
            game_name = stream["game_name"]
            viewer_count = int(stream["viewer_count"])

            has_completed_game = await _player_has_completed_game(
                db, player.id, game_name
            )

            avatar_url = _get_twitch_user_avatar(username)
            if avatar_url and avatar_url != player.avatar_link:
                player.avatar_link = avatar_url

            if game_name != player.current_game or not player.is_online:
                if not has_completed_game:
                    player.is_online = 1
                    player.online_count = viewer_count
                    player.current_game = game_name
                    game_cover = await _get_game_cover(db, game_name)
                    player.current_game_cover = game_cover

                    player.current_game_updated_at = utc_now_ts()

                    await save_category_history(db, player.id, game_name)
                    return True
                else:
                    player.is_online = 1
                    player.online_count = viewer_count
                    return True
            else:
                player.online_count = viewer_count
                return True
        else:
            if player.is_online:
                player.is_online = 0
                player.online_count = 0

                await save_category_history(db, player.id, "Offline")
                return True

    except Exception as e:
        logger.error(f"Error checking Twitch for {player.username}: {str(e)}")

        raise

    return False


async def _check_vk_stream(player: User, db: AsyncSession) -> bool:
    try:
        response = requests.get(player.vk_stream_link, timeout=110)
        response.raise_for_status()

        content = html.fromstring(response.content)

        category_xpath = content.xpath(
            "/html/body/div[1]/div/div[2]/div[2]/div/div[3]/div[1]/div[1]/div/div[2]/div[1]/div/a"
        )
        online_count_xpath = content.xpath(
            "/html/body/div[1]/div/div[2]/div[2]/div/div[3]/div[1]/div[1]/div/div[1]/div[2]/div[2]/div[2]/div[2]/div"
        )

        if len(category_xpath) != 0 and "StreamStatus_text" in response.text:
            category = category_xpath[0].text
            online_count = int(online_count_xpath[0].text.replace(",", ""))

            has_completed_game = await _player_has_completed_game(
                db, player.id, category
            )

            avatar_url = _get_vk_user_avatar(player.vk_stream_link)
            if avatar_url and avatar_url != player.avatar_link:
                player.avatar_link = avatar_url

            if category != player.current_game or not player.is_online:
                if not has_completed_game:
                    player.is_online = 1
                    player.online_count = online_count
                    player.current_game = category
                    game_cover = await _get_game_cover(db, category)
                    player.current_game_cover = game_cover

                    player.current_game_updated_at = utc_now_ts()

                    await save_category_history(db, player.id, category)
                    return True
                else:
                    player.is_online = 1
                    player.online_count = online_count
                    return True
            else:
                player.online_count = online_count
                return True
        else:
            if player.is_online:
                player.is_online = 0
                player.online_count = 0

                await save_category_history(db, player.id, "Offline")
                return True

    except Exception as e:
        logger.error(f"Error checking VK Play for {player.username}: {str(e)}")
        raise

    return False


async def _check_kick_stream(player: User, db: AsyncSession) -> bool:
    try:
        username = player.kick_stream_link.rsplit("/", 1)[1]
        data = _get_kick_channel_data(username)

        if not data:
            return False

        is_online = "livestream" in data and data["livestream"] is not None
        avatar_url = data.get("user", {}).get("profile_pic")

        if avatar_url and avatar_url != player.avatar_link:
            player.avatar_link = avatar_url

        if is_online:
            livestream = data["livestream"]
            categories = livestream.get("categories", [])

            if len(categories) > 0:
                first_category = categories[0]
                game_name = first_category.get("name", "Unknown")
                viewer_count = int(first_category.get("viewers", 0))
            else:
                game_name = "Just Chatting"
                viewer_count = 0

            has_completed_game = await _player_has_completed_game(
                db, player.id, game_name
            )

            if game_name != player.current_game or not player.is_online:
                if not has_completed_game:
                    player.is_online = 1
                    player.online_count = viewer_count
                    player.current_game = game_name
                    game_cover = await _get_game_cover(db, game_name)
                    player.current_game_cover = game_cover

                    player.current_game_updated_at = utc_now_ts()

                    await save_category_history(db, player.id, game_name)
                    return True
                else:
                    player.is_online = 1
                    player.online_count = viewer_count
                    return True
            else:
                player.online_count = viewer_count
                return True
        else:
            if player.is_online:
                player.is_online = 0
                player.online_count = 0

                await save_category_history(db, player.id, "Offline")
                return True

    except Exception as e:
        logger.error(f"Error checking Kick for {player.username}: {str(e)}")
        raise

    return False
