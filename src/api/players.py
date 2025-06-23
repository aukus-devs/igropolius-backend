import json
from typing import Annotated, cast
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api_models import (
    BonusCard,
    BonusCardEvent,
    EventsList,
    GameEvent,
    MakePlayerMove,
    MoveEvent,
    SavePlayerGame,
    ScoreChangeEvent,
    UpdatePlayerTurnState,
    UserGame,
    UserSummary,
    UsersList,
)
from src.db import get_db
from src.db_models import (
    DiceRoll,
    IgdbGame,
    PlayerCard,
    PlayerGame,
    PlayerMove,
    PlayerScoreChange,
    User,
)
from src.enums import (
    GameCompletionType,
    MainBonusCardType,
    PlayerMoveType,
    ScoreChangeType,
)
from src.utils.auth import get_current_user
from src.utils.category_history import (
    calculate_game_duration_by_title,
    get_current_game_duration,
    save_category_history,
)
from src.utils.common import map_bonus_card_to_event_type
from src.utils.db import safe_commit, utc_now_ts


router = APIRouter(tags=["players"])


@router.get("/api/players", response_model=UsersList)
async def get_users(db: Annotated[AsyncSession, Depends(get_db)]):
    users_query = await db.execute(select(User).filter(User.is_active == 1))
    users = users_query.scalars().all()
    games_query = await db.execute(select(PlayerGame))
    games = games_query.scalars().all()
    cards_query = await db.execute(
        select(PlayerCard).where(PlayerCard.status == "active")
    )
    cards = cards_query.scalars().all()

    game_ids = {g.game_id for g in games if g.game_id is not None}
    igdb_games_dict = {}
    if game_ids:
        igdb_games_query = await db.execute(
            select(IgdbGame).where(IgdbGame.id.in_(game_ids))
        )
        igdb_games = igdb_games_query.scalars().all()
        igdb_games_dict = {game.id: game for game in igdb_games}

    users_models = []
    for user in users:
        model = UserSummary.model_validate(user)
        model.games = [
            UserGame(
                sector_id=g.sector_id,
                title=g.item_title,
                length=g.item_length,
                created_at=g.created_at,
                status=cast(GameCompletionType, g.type),
                review=g.item_review,
                rating=g.item_rating,
                duration=g.duration,
                vod_links=g.vod_links,
                cover=igdb_games_dict[g.game_id].cover
                if g.game_id and g.game_id in igdb_games_dict
                else None,
            )
            for g in games
            if g.player_id == user.id
        ]
        model.games.sort(key=lambda x: x.created_at, reverse=True)

        model.bonus_cards = [
            BonusCard(
                bonus_type=c.card_type,
                received_at=c.created_at,
                received_on_sector=c.received_on_sector,
            )
            for c in cards
            if c.player_id == user.id
        ]

        model.current_game_duration = await get_current_game_duration(
            db, user.id, user.current_game
        )

        users_models.append(model)
    return {"players": users_models}


@router.get("/api/players/{player_id}/events", response_model=EventsList)
async def get_player_events(
    player_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    moves_query = await db.execute(
        select(PlayerMove).where(PlayerMove.player_id == player_id)
    )
    moves = moves_query.scalars().all()
    move_events = []
    for e in moves:
        dice_roll = []
        dice_roll_json = None
        if e.random_org_roll:
            dice_roll_query = await db.execute(
                select(DiceRoll).where(DiceRoll.id == e.random_org_roll)
            )
            dice_roll_record = dice_roll_query.scalars().first()
            if dice_roll_record:
                dice_roll = json.loads(dice_roll_record.dice_values)
                dice_roll_json = json.loads(dice_roll_record.json_short_data)

        used_cards_query = await db.execute(
            select(PlayerCard).where(
                PlayerCard.player_id == player_id,
                PlayerCard.status == "used",
                PlayerCard.used_on_sector == e.sector_to,
                PlayerCard.used_at >= e.created_at - 60,
                PlayerCard.used_at <= e.created_at + 60,
            )
        )
        used_cards = used_cards_query.scalars().all()
        bonuses_used = [MainBonusCardType(card.card_type) for card in used_cards]

        move_events.append(
            MoveEvent(
                subtype=PlayerMoveType(e.move_type),
                sector_from=e.sector_from,
                sector_to=e.sector_to,
                map_completed=bool(e.map_completed),
                adjusted_roll=e.adjusted_roll,
                dice_roll=dice_roll,
                dice_roll_json=dice_roll_json,
                timestamp=e.created_at,
                bonuses_used=bonuses_used,
            )
        )

    games_query = await db.execute(
        select(PlayerGame).where(PlayerGame.player_id == player_id)
    )
    games = games_query.scalars().all()

    game_ids = {g.game_id for g in games if g.game_id is not None}
    igdb_games_dict = {}
    if game_ids:
        igdb_games_query = await db.execute(
            select(IgdbGame).where(IgdbGame.id.in_(game_ids))
        )
        igdb_games = igdb_games_query.scalars().all()
        igdb_games_dict = {game.id: game for game in igdb_games}

    game_events = [
        GameEvent(
            subtype=GameCompletionType(e.type),
            game_title=e.item_title,
            game_cover=igdb_games_dict[e.game_id].cover
            if e.game_id and e.game_id in igdb_games_dict
            else None,
            sector_id=e.sector_id,
            timestamp=e.created_at,
        )
        for e in games
    ]

    cards_query = await db.execute(
        select(PlayerCard).where(PlayerCard.player_id == player_id)
    )
    cards = cards_query.scalars().all()
    bonus_card_events = [
        BonusCardEvent(
            subtype=map_bonus_card_to_event_type(e),
            bonus_type=MainBonusCardType(e.card_type),
            sector_id=e.received_on_sector,
            timestamp=e.created_at,
            used_at=e.used_at,
            used_on_sector=e.used_on_sector,
            lost_at=e.lost_at,
            lost_on_sector=e.lost_on_sector,
            stolen_at=e.stolen_at,
            stolen_from_player=e.stolen_from_player,
            stolen_by=e.stolen_by,
        )
        for e in cards
    ]

    scores_query = await db.execute(
        select(PlayerScoreChange).where(PlayerScoreChange.player_id == player_id)
    )
    score_changes = scores_query.scalars().all()
    score_change_events = [
        ScoreChangeEvent(
            subtype=ScoreChangeType(e.change_type),
            amount=e.score_change,
            reason=e.description,
            sector_id=e.sector_id,
            timestamp=e.created_at,
        )
        for e in score_changes
    ]
    all_events = move_events + game_events + bonus_card_events + score_change_events
    return {"events": all_events}


@router.post("/api/players/current/moves")
async def do_player_move(
    move: MakePlayerMove,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    dice_roll_query = await db.execute(
        select(DiceRoll)
        .where(DiceRoll.player_id == current_user.id, DiceRoll.used == 0)
        .order_by(DiceRoll.created_at.desc())
        .limit(1)
    )
    dice_roll_record = dice_roll_query.scalars().first()

    if not dice_roll_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No dice roll available. Please roll dice first.",
        )

    if move.bonuses_used:
        player_cards_query = await db.execute(
            select(PlayerCard).where(
                PlayerCard.player_id == current_user.id, PlayerCard.status == "active"
            )
        )
        player_cards = player_cards_query.scalars().all()
        available_bonuses = [card.card_type for card in player_cards]

        for bonus in move.bonuses_used:
            if bonus.value not in available_bonuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Player does not have active bonus card: {bonus.value}",
                )

    dice_values = json.loads(dice_roll_record.dice_values)
    roll_result = sum(dice_values)

    if MainBonusCardType.CHOOSE_1_DIE in move.bonuses_used:
        if move.selected_die is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="selected_die must be specified when using CHOOSE_1_DIE bonus",
            )
        if move.selected_die < 0 or move.selected_die >= len(dice_values):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"selected_die must be between 0 and {len(dice_values) - 1}",
            )
        roll_result = dice_values[move.selected_die]
    elif move.selected_die is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="selected_die can only be used with CHOOSE_1_DIE bonus",
        )

    if MainBonusCardType.ADJUST_BY_1 in move.bonuses_used:
        roll_result += 1

    sector_to = current_user.sector_id + roll_result
    map_completed = False
    if sector_to > 40:
        sector_to = sector_to % 40
        map_completed = True

    move_item = PlayerMove(
        player_id=current_user.id,
        sector_from=current_user.sector_id,
        sector_to=sector_to,
        move_type=move.type.value,
        map_completed=map_completed,
        adjusted_roll=roll_result,
        random_org_roll=dice_roll_record.id,
    )
    db.add(move_item)
    current_user.sector_id = sector_to
    if map_completed:
        current_user.maps_completed += 1

    dice_roll_record.used = 1

    if move.bonuses_used:
        for bonus in move.bonuses_used:
            card_to_use_query = await db.execute(
                select(PlayerCard)
                .where(
                    PlayerCard.player_id == current_user.id,
                    PlayerCard.card_type == bonus.value,
                    PlayerCard.status == "active",
                )
                .limit(1)
            )
            card_to_use = card_to_use_query.scalars().first()
            if card_to_use:
                card_to_use.status = "used"
                card_to_use.used_at = utc_now_ts()
                card_to_use.used_on_sector = current_user.sector_id

    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/player-games")
async def save_player_game(
    request: SavePlayerGame,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        game_duration = await calculate_game_duration_by_title(
            db, request.title, current_user.id
        )
    except Exception:
        game_duration = 0

    game = PlayerGame(
        player_id=current_user.id,
        type=request.status.value,
        item_title=request.title,
        item_review=request.review,
        item_rating=request.rating,
        item_length=request.length,
        vod_links=request.vod_links,
        sector_id=current_user.sector_id,
        game_id=request.game_id,
        duration=game_duration,
    )
    db.add(game)

    score_change = PlayerScoreChange(
        player_id=current_user.id,
        score_change=request.scores,
        change_type=ScoreChangeType.GAME_COMPLETED.value,
        description=f"game completed: '{request.title}'",
        sector_id=current_user.sector_id,
    )
    db.add(score_change)

    current_user.total_score += request.scores
    current_user.current_game = None
    current_user.current_game_updated_at = None
    current_user.current_game_cover = None
    await save_category_history(db, current_user.id, "NewPlayerGame")

    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/players/current/turn-state")
async def update_turn_state(
    request: UpdatePlayerTurnState,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user.turn_state = request.turn_state.value
    await safe_commit(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
