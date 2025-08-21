from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import PlayerStats, PlayerStatsResponse
from src.db.db_models import PlayerCard, PlayerGame, PlayerScoreChange, User
from src.db.db_session import get_db
from src.enums import GameCompletionType, ScoreChangeType
from src.utils.common import InstantCardsValues

router = APIRouter(tags=["stats"])


@router.get("/api/stats", response_model=PlayerStatsResponse)
async def get_player_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    players_query = await db.execute(
        select(User).filter(User.is_active == 1, User.sector_id.is_not(None))
    )
    players = players_query.scalars().all()
    player_ids = [player.id for player in players]

    game_stats_query = await db.execute(
        select(
            PlayerGame.player_id,
            func.count(
                case((PlayerGame.type == GameCompletionType.COMPLETED.value, 1))
            ).label("games_completed"),
            func.count(
                case((PlayerGame.type == GameCompletionType.DROP.value, 1))
            ).label("games_dropped"),
        )
        .select_from(PlayerGame)
        .where(PlayerGame.player_id.in_(player_ids))
        .group_by(PlayerGame.player_id)
    )
    game_stats = {row.player_id: row for row in game_stats_query.all()}

    score_stats_query = await db.execute(
        select(
            PlayerScoreChange.player_id,
            func.sum(
                case(
                    (
                        PlayerScoreChange.change_type
                        == ScoreChangeType.GAME_COMPLETED.value,
                        PlayerScoreChange.score_change,
                    ),
                    else_=0,
                )
            ).label("score_from_games_completed"),
            func.sum(
                case(
                    (
                        PlayerScoreChange.change_type
                        == ScoreChangeType.GAME_DROPPED.value,
                        PlayerScoreChange.score_change,
                    ),
                    else_=0,
                )
            ).label("score_from_games_dropped"),
            func.sum(
                case(
                    (
                        (
                            PlayerScoreChange.change_type
                            == ScoreChangeType.INSTANT_CARD.value
                        )
                        & (PlayerScoreChange.score_change > 0),
                        PlayerScoreChange.score_change,
                    ),
                    else_=0,
                )
            ).label("score_from_cards"),
            func.sum(
                case(
                    (
                        (
                            PlayerScoreChange.change_type
                            == ScoreChangeType.INSTANT_CARD.value
                        )
                        & (PlayerScoreChange.score_change < 0),
                        PlayerScoreChange.score_change,
                    ),
                    else_=0,
                )
            ).label("score_lost_on_cards"),
            func.sum(
                case(
                    (
                        (
                            PlayerScoreChange.change_type
                            == ScoreChangeType.STREET_TAX.value
                        )
                        & (PlayerScoreChange.score_change < 0),
                        PlayerScoreChange.score_change,
                    ),
                    else_=0,
                )
            ).label("street_tax_paid"),
            func.sum(
                case(
                    (
                        (PlayerScoreChange.change_type == ScoreChangeType.MAP_TAX.value)
                        & (PlayerScoreChange.score_change < 0),
                        PlayerScoreChange.score_change,
                    ),
                    else_=0,
                )
            ).label("map_tax_paid"),
            func.sum(
                case(
                    (
                        (
                            PlayerScoreChange.change_type
                            == ScoreChangeType.STREET_INCOME.value
                        )
                        & (PlayerScoreChange.score_change > 0),
                        PlayerScoreChange.score_change,
                    ),
                    else_=0,
                )
            ).label("income_from_others"),
        )
        .select_from(PlayerScoreChange)
        .where(PlayerScoreChange.player_id.in_(player_ids))
        .group_by(PlayerScoreChange.player_id)
    )
    score_stats = {row.player_id: row for row in score_stats_query.all()}

    instant_cards_used_query = await db.execute(
        select(PlayerCard.player_id, func.count().label("instant_cards_used"))
        .select_from(PlayerCard)
        .where(
            PlayerCard.player_id.in_(player_ids),
            PlayerCard.status == "used",
            PlayerCard.card_type.in_(InstantCardsValues),
        )
        .group_by(PlayerCard.player_id)
    )
    instant_cards_used = {row.player_id: row for row in instant_cards_used_query.all()}

    player_stats_list = []
    for player in players:
        gs = game_stats.get(player.id)
        ss = score_stats.get(player.id)
        cs = instant_cards_used.get(player.id)

        player_stats = PlayerStats(
            total_score=player.total_score if player.total_score else 0.0,
            player_id=player.id,
            username=player.username,
            games_completed=gs.games_completed if gs else 0,
            games_dropped=gs.games_dropped if gs else 0,
            score_from_games_completed=round(ss.score_from_games_completed, 2)
            if ss
            else 0,
            score_from_games_dropped=round(ss.score_from_games_dropped, 2) if ss else 0,
            instant_cards_used=cs.instant_cards_used if cs else 0,
            score_from_cards=round(ss.score_from_cards, 2) if ss else 0,
            score_lost_on_cards=round(ss.score_lost_on_cards, 2) if ss else 0,
            street_tax_paid=round(ss.street_tax_paid, 2) if ss else 0,
            map_tax_paid=round(ss.map_tax_paid, 2) if ss else 0,
            income_from_others=round(ss.income_from_others, 2) if ss else 0,
        )
        player_stats_list.append(player_stats)

    return PlayerStatsResponse(stats=player_stats_list)
