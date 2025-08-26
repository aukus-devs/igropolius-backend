from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import (
    FinalStatsResponse,
    PlayerFinalStats,
    PlayerGame as PlayerGameModel,
    PlayerStats,
    PlayerStatsResponse,
)
from src.db.db_models import (
    DiceRoll,
    PlayerCard,
    PlayerGame,
    PlayerMove,
    PlayerScoreChange,
    User,
)
from src.db.db_session import get_db
from src.enums import (
    BonusCardStatus,
    GameCompletionType,
    PlayerMoveType,
    ScoreChangeType,
)
from src.consts import INSTANT_CARD_TYPES
from src.utils.common import get_prison_user

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
            PlayerCard.card_type.in_(INSTANT_CARD_TYPES),
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


@router.get("/api/stats/final", response_model=FinalStatsResponse)
async def get_final_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    active_players_query = await db.execute(select(User).filter(User.is_active == 1))
    active_players = active_players_query.scalars().all()

    prison_user = await get_prison_user(db)

    total_score = sum(player.total_score or 0 for player in active_players)

    all_player_games_query = await db.execute(select(PlayerGame))
    all_player_games: list[PlayerGame] = all_player_games_query.scalars().all()
    games_by_player: dict[int, list[PlayerGame]] = {}
    for game in all_player_games:
        if game.player_id not in games_by_player:
            games_by_player[game.player_id] = []
        games_by_player[game.player_id].append(game)

    all_player_cards_query = await db.execute(
        select(PlayerCard).filter(
            PlayerCard.player_id != prison_user.id if prison_user else True
        )
    )
    all_player_cards: list[PlayerCard] = all_player_cards_query.scalars().all()
    cards_by_player: dict[int, list[PlayerCard]] = {}
    for card in all_player_cards:
        if card.player_id not in cards_by_player:
            cards_by_player[card.player_id] = []
        cards_by_player[card.player_id].append(card)

    completed_games_list = [
        game
        for game in all_player_games
        if game.type == GameCompletionType.COMPLETED.value
    ]

    completed_games = len(completed_games_list)

    dice_rolls_query = await db.execute(select(func.count(DiceRoll.id)))
    dice_rolls = dice_rolls_query.scalar_one()

    hours_spent_on_games_query = await db.execute(select(func.sum(PlayerGame.duration)))
    hours_spent_on_games = (hours_spent_on_games_query.scalar_one() or 0) / 3600

    cards_received = len(all_player_cards)

    cards_used = len(
        [card for card in all_player_cards if card.status == BonusCardStatus.USED.value]
    )

    maps_completed = sum(player.maps_completed or 0 for player in active_players)

    games_dropped_or_rerolled = len(
        [
            game
            for game in all_player_games
            if game.type
            in (GameCompletionType.DROP.value, GameCompletionType.REROLL.value)
        ]
    )

    train_rides_query = await db.execute(
        select(func.count(PlayerMove.id)).filter(
            PlayerMove.move_type == PlayerMoveType.TRAIN_RIDE.value
        )
    )
    train_rides = train_rides_query.scalar_one()

    average_rating_of_completed_games = 0.0
    if completed_games_list:
        average_rating_of_completed_games = round(
            sum(game.item_rating for game in completed_games_list)
            / len(completed_games_list),
            2,
        )

    player_stats_list = []
    for player in active_players:
        player_games = games_by_player.get(player.id, [])

        games_completed = len(
            [g for g in player_games if g.type == GameCompletionType.COMPLETED.value]
        )
        games_dropped = len(
            [g for g in player_games if g.type == GameCompletionType.DROP.value]
        )

        durations = [g.duration for g in player_games if g.duration]
        longest_game_hours = max(durations) / 3600 if durations else 0
        shortest_game_hours = min(durations) / 3600 if durations else 0
        hours_played = sum(durations) / 3600 if durations else 0

        player_cards = cards_by_player.get(player.id, [])
        cards_amount = len(player_cards)

        completed_games_list = [
            g for g in player_games if g.type == GameCompletionType.COMPLETED.value
        ]
        best_rated_game = (
            max(completed_games_list, key=lambda g: g.item_rating)
            if completed_games_list
            else None
        )
        worst_rated_game = (
            min(completed_games_list, key=lambda g: g.item_rating)
            if completed_games_list
            else None
        )

        player_stats = PlayerFinalStats(
            player_id=player.id,
            username=player.username,
            total_score=player.total_score or 0,
            games_completed=games_completed,
            games_dropped=games_dropped,
            longest_game_hours=longest_game_hours,
            shortest_game_hours=shortest_game_hours,
            cards_amount=cards_amount,
            hours_played=hours_played,
            best_rated_game=PlayerGameModel.model_validate(best_rated_game)
            if best_rated_game
            else None,
            worst_rated_game=PlayerGameModel.model_validate(worst_rated_game)
            if worst_rated_game
            else None,
        )
        player_stats_list.append(player_stats)

    return FinalStatsResponse(
        total_score=total_score,
        completed_games=completed_games,
        dice_rolls=dice_rolls,
        hours_spent_on_games=hours_spent_on_games,
        cards_received=cards_received,
        cards_used=cards_used,
        maps_completed=maps_completed,
        games_dropped_or_rerolled=games_dropped_or_rerolled,
        train_rides=train_rides,
        average_rating_of_completed_games=average_rating_of_completed_games,
        players=player_stats_list,
    )
