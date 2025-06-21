import requests
from lxml import html
import os
import logging
from typing import Dict, Any
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


async def _player_has_completed_game(db: AsyncSession, player_id: int, game_name: str) -> bool:
    query = await db.execute(
        select(PlayerGame)
        .where(PlayerGame.player_id == player_id)
        .where(PlayerGame.item_title == game_name)
        .limit(1)
    )
    
    existing_game = query.scalars().first()
    return existing_game is not None


async def _get_game_cover(db: AsyncSession, game_name: str) -> str | None:
    query = await db.execute(
        select(IgdbGame.cover)
        .where(IgdbGame.name.ilike(f'%{game_name}%'))
        .limit(1)
    )
    
    result = query.scalar_one_or_none()
    return result


async def refresh_stream_statuses(db: AsyncSession) -> Dict[str, Any]:
    stats = {
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

            has_completed_game = await _player_has_completed_game(db, player.id, game_name)

            if game_name != player.current_game or not player.is_online:
                if not has_completed_game:
                    player.is_online = 1
                    player.online_count = viewer_count
                    player.current_game = game_name
                    if not player.current_game_cover:
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

            has_completed_game = await _player_has_completed_game(db, player.id, category)

            if category != player.current_game or not player.is_online:
                if not has_completed_game:
                    player.is_online = 1
                    player.online_count = online_count
                    player.current_game = category
                    if not player.current_game_cover:
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
    return False
