import json
from itertools import chain
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import (
    ActiveBonusCard,
    EditPlayerGame,
    GameDurationRequest,
    GameDurationResponse,
    GameEvent,
    MoveEvent,
    MovePlayerGameRequest,
    PlayerDetails,
    PlayerEventsResponse,
    PlayerListResponse,
    PlayerMoveRequest,
    PlayerMoveResponse,
    SavePlayerGameRequest,
    SavePlayerGameResponse,
    ScoreChangeEvent,
    UpdatePlayerRequest,
    UpdatePlayerTurnStateRequest,
)
from src.api_models import (
    PlayerGame as PlayerGameApiModel,
)
from src.consts import (
    BONUS_SECTORS,
    BUILDING_SECTORS,
    DROP_SCORE_LOST_MINIMUM,
    DROP_SCORE_LOST_PERCENT,
    GAME_LENGTHS_IN_ORDER,
    PARKING_SECTOR_ID,
    SCORE_BONUS_PER_MAP_COMPLETION,
    SCORES_BY_GAME_LENGTH,
    START_SECTOR_ID,
    TRAIN_MAP,
)
from src.db.db_models import (
    DiceRoll,
    IgdbGame,
    PlayerCard,
    PlayerMove,
    PlayerScoreChange,
    User,
)
from src.db.db_models import (
    PlayerGame as PlayerGameDbModel,
)
from src.db.db_session import get_db
from src.db.queries.category_history import (
    calculate_game_duration_by_title,
    get_current_game_duration,
    save_category_history,
)
from src.db.queries.notifications import (
    create_game_completed_notification,
    create_game_drop_notification,
    create_game_reroll_notification,
)
from src.db.queries.players import change_player_score
from src.enums import (
    BonusCardStatus,
    GameCompletionType,
    GameDifficulty,
    MainBonusCardType,
    PlayerMoveType,
    PlayerTurnState,
    Role,
    ScoreChangeType,
)
from src.utils.auth import get_current_user_for_update
from src.utils.common import (
    get_bonus_cards_dropped_events,
    get_bonus_cards_looted_events,
    get_bonus_cards_received_events,
    get_bonus_cards_stolen_events,
    get_bonus_cards_used_events,
    get_closest_prison_sector,
    get_prison_user,
    get_sector_score_multiplier,
)
from src.utils.db import utc_now_ts

router = APIRouter(tags=["players"])


@router.get("/api/players", response_model=PlayerListResponse)
async def get_players(db: Annotated[AsyncSession, Depends(get_db)]):
    players_query = await db.execute(
        select(User)
        .filter(User.is_active == 1)
        .filter(User.sector_id.isnot(None))
        .filter(User.total_score.isnot(None))
        .filter(User.turn_state.isnot(None), User.turn_state != "")
    )
    players = players_query.scalars().all()
    games_query = await db.execute(select(PlayerGameDbModel))
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

    game_score_changes_query = select(PlayerScoreChange).where(
        PlayerScoreChange.id.in_(
            [g.score_change_id for g in games if g.score_change_id is not None]
        ),
    )
    game_score_changes = await db.execute(game_score_changes_query)
    game_score_changes = game_score_changes.scalars().all()
    score_changes_by_id = {
        change.id: change.score_change for change in game_score_changes
    }

    users_models = []
    for user in players:
        model = PlayerDetails.model_validate(user)
        model.games = [
            PlayerGameApiModel(
                id=g.id,
                player_id=g.player_id,
                sector_id=g.sector_id,
                title=g.item_title,
                length=g.item_length,
                length_bonus=g.item_length_bonus,
                created_at=g.created_at,
                status=cast(GameCompletionType, g.type),
                review=g.item_review,
                rating=g.item_rating,
                duration=g.duration,
                vod_links=g.vod_links,
                cover=igdb_games_dict[g.game_id].cover
                if g.game_id and g.game_id in igdb_games_dict
                else None,
                game_id=g.game_id
                if g.game_id and g.game_id in igdb_games_dict
                else None,
                difficulty_level=GameDifficulty(g.difficulty_level),
                score_change_amount=score_changes_by_id.get(g.score_change_id),
            )
            for g in games
            if g.player_id == user.id
        ]
        model.games.sort(key=lambda x: x.created_at, reverse=True)

        model.bonus_cards = [
            ActiveBonusCard(
                bonus_type=MainBonusCardType(c.card_type),
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

    prison_user = await get_prison_user(db)
    if not prison_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prison user not found.",
        )

    prison_query = await db.execute(
        select(PlayerCard).where(
            PlayerCard.player_id == prison_user.id,
            PlayerCard.status == BonusCardStatus.ACTIVE.value,
        )
    )
    prison_cards = prison_query.scalars().all()
    prison_cards_bonuses = [MainBonusCardType(card.card_type) for card in prison_cards]

    return PlayerListResponse(players=users_models, prison_cards=prison_cards_bonuses)


@router.get("/api/players/{player_id}/events", response_model=PlayerEventsResponse)
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
                PlayerCard.player_move_id == e.id,
            )
        )
        used_cards = used_cards_query.scalars().all()
        bonuses_used = [MainBonusCardType(card.card_type) for card in used_cards]

        move_events.append(
            MoveEvent(
                event_type="player-move",
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
        select(PlayerGameDbModel).where(PlayerGameDbModel.player_id == player_id)
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
            event_type="game",
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

    received_card_events = get_bonus_cards_received_events(cards)
    used_card_events = get_bonus_cards_used_events(cards)
    stolen_card_events = get_bonus_cards_stolen_events(cards)
    dropped_card_events = get_bonus_cards_dropped_events(cards)
    looted_card_events = get_bonus_cards_looted_events(cards)
    bonus_card_events = chain(
        received_card_events,
        used_card_events,
        stolen_card_events,
        dropped_card_events,
        looted_card_events,
    )

    scores_query = await db.execute(
        select(PlayerScoreChange).where(PlayerScoreChange.player_id == player_id)
    )
    score_changes = scores_query.scalars().all()
    score_change_events = []
    for e in score_changes:
        player_card = None
        if e.player_card_id:
            player_card_query = await db.execute(
                select(PlayerCard).where(PlayerCard.id == e.player_card_id)
            )
            player_card = player_card_query.scalars().first()

        event = ScoreChangeEvent(
            event_type="score-change",
            subtype=ScoreChangeType(e.change_type),
            amount=e.score_change,
            reason=e.description,
            sector_id=e.sector_id,
            timestamp=e.created_at,
            score_before=e.score_before,
            score_after=e.score_after,
            income_from_player=e.income_from_player,
            bonus_card=e.bonus_card,
            bonus_card_owner=e.bonus_card_owner,
            instant_card_score_multiplier=player_card.instant_card_score_multiplier
            if player_card
            else None,
        )
        score_change_events.append(event)

    all_events = chain(move_events, game_events, bonus_card_events, score_change_events)
    return {"events": all_events}


@router.post("/api/players/current/moves", response_model=PlayerMoveResponse)
async def do_player_move(
    request: PlayerMoveRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if (
        current_user.sector_id is None
        or current_user.maps_completed is None
        or current_user.total_score is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player data is not set",
        )

    original_sector = current_user.sector_id
    map_completed = False

    roll_result = None
    dice_roll_record_id = -1

    choose_1_die_card = None
    adjust_by1_card = None

    match request.type:
        case PlayerMoveType.DICE_ROLL:
            dice_roll_query = await db.execute(
                select(DiceRoll)
                .where(DiceRoll.player_id == current_user.id, DiceRoll.used == 0)
                .order_by(DiceRoll.created_at.desc())
                .limit(1)
                .with_for_update()
            )
            dice_roll_record = dice_roll_query.scalars().first()

            if not dice_roll_record:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No dice roll available. Please roll dice first.",
                )

            dice_roll_record.used = 1
            dice_roll_record_id = dice_roll_record.id

            dice_values: list[int] = json.loads(dice_roll_record.dice_values)
            roll_result = sum(dice_values)

            if request.selected_die is not None:
                choose_1_die_card_query = await db.execute(
                    select(PlayerCard)
                    .where(
                        PlayerCard.player_id == current_user.id,
                        PlayerCard.status == "active",
                        PlayerCard.card_type == MainBonusCardType.CHOOSE_1_DIE.value,
                    )
                    .with_for_update()
                )
                choose_1_die_card = choose_1_die_card_query.scalars().first()

                if choose_1_die_card is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Player does not have active bonus card: {MainBonusCardType.CHOOSE_1_DIE.value}",
                    )
                if request.selected_die not in dice_values:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"selected_die must be one of the rolled dice: {dice_values}",
                    )
                roll_result = request.selected_die
                choose_1_die_card.status = BonusCardStatus.USED.value
                choose_1_die_card.used_at = utc_now_ts()
                choose_1_die_card.used_on_sector = original_sector

            if request.adjust_by_1 is not None:
                adjust_by1_card_query = await db.execute(
                    select(PlayerCard)
                    .where(
                        PlayerCard.player_id == current_user.id,
                        PlayerCard.status == "active",
                        PlayerCard.card_type == MainBonusCardType.ADJUST_BY_1.value,
                    )
                    .with_for_update()
                )
                adjust_by1_card = adjust_by1_card_query.scalars().first()

                if adjust_by1_card is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Player does not have active bonus card: {MainBonusCardType.ADJUST_BY_1.value}",
                    )
                if request.adjust_by_1 not in [-1, 1]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="adjust_by_1 must be either -1 or 1",
                    )
                roll_result += request.adjust_by_1
                adjust_by1_card.status = BonusCardStatus.USED.value
                adjust_by1_card.used_at = utc_now_ts()
                adjust_by1_card.used_on_sector = original_sector

            if request.ride_train:
                train_target = TRAIN_MAP.get(current_user.sector_id)
                if not train_target:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Player must be on a train sector to use ride train option.",
                    )

                map_completed = original_sector > train_target
                train_move = PlayerMove(
                    player_id=current_user.id,
                    sector_from=current_user.sector_id,
                    sector_to=train_target,
                    move_type=PlayerMoveType.TRAIN_RIDE.value,
                    map_completed=map_completed,
                    adjusted_roll=10,
                    random_org_roll=-1,
                )
                db.add(train_move)
                current_user.sector_id = train_target

        # case PlayerMoveType.TRAIN_RIDE:
        #     roll_result = 10
        case PlayerMoveType.DROP_TO_PRISON:
            # move player to prison
            prison_sector = get_closest_prison_sector(current_user.sector_id)
            roll_result = prison_sector - current_user.sector_id
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid move type: {request.type}",
            )

    if roll_result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid move type or missing roll result.",
        )

    sector_to = current_user.sector_id + roll_result
    if sector_to > 40:
        sector_to = sector_to % 40
        map_completed = True

    move_item = PlayerMove(
        player_id=current_user.id,
        sector_from=current_user.sector_id,
        sector_to=sector_to,
        move_type=request.type.value,
        map_completed=map_completed,
        adjusted_roll=roll_result,
        random_org_roll=dice_roll_record_id,
    )
    db.add(move_item)
    await db.flush()

    if choose_1_die_card:
        choose_1_die_card.player_move_id = move_item.id
    if adjust_by1_card:
        adjust_by1_card.player_move_id = move_item.id

    current_user.sector_id = sector_to
    if map_completed:
        current_user.maps_completed += 1

    return {"new_sector_id": sector_to, "map_completed": map_completed}


@router.post("/api/player-games", response_model=SavePlayerGameResponse)
async def save_player_game(
    request: SavePlayerGameRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if (
        current_user.sector_id is None
        or current_user.maps_completed is None
        or current_user.total_score is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player data is not set",
        )

    game_duration = await calculate_game_duration_by_title(
        db, request.title, current_user.id
    )

    target_sector = current_user.sector_id

    game = PlayerGameDbModel(
        player_id=current_user.id,
        type=request.status.value,
        item_title=request.title,
        item_review=request.review,
        item_rating=request.rating,
        item_length=request.length.value,
        vod_links=request.vod_links,
        sector_id=target_sector,
        player_sector_id=current_user.sector_id,
        game_id=request.game_id,
        duration=game_duration,
        item_length_bonus=0,
    )
    db.add(game)

    if (
        request.difficulty_level
        and request.difficulty_level != GameDifficulty.NORMAL
        and request.status != GameCompletionType.REROLL
    ):
        game.difficulty_level = request.difficulty_level.value
        current_user.game_difficulty_level = 0

    match request.status:
        case GameCompletionType.COMPLETED:
            if game.item_length not in GAME_LENGTHS_IN_ORDER:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid game length: {game.item_length}. Must be one of {GAME_LENGTHS_IN_ORDER}.",
                )

            multiplier = get_sector_score_multiplier(target_sector)
            base_scores = SCORES_BY_GAME_LENGTH[request.length.value]
            map_completion_bonus = (
                current_user.maps_completed * SCORE_BONUS_PER_MAP_COMPLETION
            )

            total_bonus = base_scores * multiplier + map_completion_bonus

            score_change = await change_player_score(
                db,
                current_user,
                total_bonus,
                ScoreChangeType.GAME_COMPLETED,
                f"game completed: '{request.title}'",
            )
            await db.flush()
            game.score_change_id = score_change.id

            await create_game_completed_notification(
                db, current_user.id, total_bonus, request.title
            )

            item_length_idx = GAME_LENGTHS_IN_ORDER.index(game.item_length)

            is_building_sector = target_sector in BUILDING_SECTORS
            if target_sector == START_SECTOR_ID:
                current_user.building_upgrade_bonus += 1
            elif target_sector == PARKING_SECTOR_ID:
                current_user.building_upgrade_bonus += 2
            elif target_sector in BONUS_SECTORS:
                current_user.building_upgrade_bonus += 2

            if current_user.building_upgrade_bonus != 0 and is_building_sector:
                bonus = current_user.building_upgrade_bonus
                bonus_step = 1 if bonus > 0 else -1
                bonus_steps = [bonus_step] * abs(bonus)
                current_stage_idx = item_length_idx
                for step in bonus_steps:
                    current_stage_idx = current_stage_idx + step
                    if current_stage_idx < 0 or current_stage_idx >= len(
                        GAME_LENGTHS_IN_ORDER
                    ):
                        break
                    game.item_length = GAME_LENGTHS_IN_ORDER[current_stage_idx]
                    game.item_length_bonus += step
                    current_user.building_upgrade_bonus -= step

        case GameCompletionType.DROP:
            score_lost = max(
                current_user.total_score * DROP_SCORE_LOST_PERCENT,
                DROP_SCORE_LOST_MINIMUM,
            )
            score_change = await change_player_score(
                db,
                current_user,
                -score_lost,
                ScoreChangeType.GAME_DROPPED,
                f"game dropped: '{request.title}'",
            )
            await db.flush()
            game.score_change_id = score_change.id
            await create_game_drop_notification(db, current_user.id, request.title)
        case GameCompletionType.REROLL:
            await create_game_reroll_notification(db, current_user.id, request.title)

    current_user.current_game = None
    current_user.current_game_updated_at = None
    current_user.current_game_cover = None
    await save_category_history(db, current_user.id, "NewPlayerGame")
    return {"new_sector_id": current_user.sector_id}


@router.post("/api/players/current/turn-state")
async def update_turn_state(
    request: UpdatePlayerTurnStateRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user.turn_state = request.turn_state.value
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/player-games/move")
async def move_player_game(
    request: MovePlayerGameRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.sector_id != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player can only move game when on sector 1.",
        )

    if current_user.turn_state != PlayerTurnState.CHOOSING_BUILDING_SECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player must be in CHOOSING_BUILDING_SECTOR state to move game.",
        )

    game_query = await db.execute(
        select(PlayerGameDbModel)
        .where(
            PlayerGameDbModel.player_id == current_user.id,
            PlayerGameDbModel.type == GameCompletionType.COMPLETED.value,
            PlayerGameDbModel.player_sector_id == 1,
            PlayerGameDbModel.sector_id == 1,
        )
        .order_by(PlayerGameDbModel.id.desc())
        .limit(1)
        .with_for_update()
    )
    game = game_query.scalars().first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed game found for the player on sector 1.",
        )

    game.sector_id = request.new_sector_id
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/api/player-games/{game_id}")
async def edit_player_game(
    game_id: int,
    request: EditPlayerGame,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    game_query = await db.execute(
        select(PlayerGameDbModel)
        .where(PlayerGameDbModel.id == game_id)
        .with_for_update()
    )
    game = game_query.scalars().first()

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    can_edit = False

    if current_user.role == Role.ADMIN.value:
        can_edit = True
    elif current_user.role == Role.PLAYER.value and game.player_id == current_user.id:
        can_edit = True
    elif (
        current_user.role == Role.MODER.value
        and current_user.moder_for == game.player_id
    ):
        can_edit = True

    if not can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this game.",
        )

    game.item_title = request.game_title
    game.item_review = request.game_review
    game.item_rating = request.rating
    game.vod_links = request.vod_links or ""
    game.game_id = request.game_id
    game.duration = await calculate_game_duration_by_title(
        db, request.game_title, game.player_id
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/players")
async def update_player(
    request: UpdatePlayerRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    same_model_query = await db.execute(
        select(User).filter(
            User.model_name == request.model_name,
            User.id != current_user.id,
            User.is_active == 1,
            User.sector_id.isnot(None),
        )
    )
    same_model_user = same_model_query.scalars().first()
    if same_model_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model name already exists for another user.",
        )

    same_color_query = await db.execute(
        select(User).filter(
            User.color == request.color,
            User.id != current_user.id,
            User.is_active == 1,
            User.sector_id.isnot(None),
        )
    )
    same_color_user = same_color_query.scalars().first()
    if same_color_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Color already exists for another user.",
        )

    current_user.model_name = request.model_name
    current_user.color = request.color
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/game-duration", response_model=GameDurationResponse)
async def get_game_duration(
    request: GameDurationRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    duration = await calculate_game_duration_by_title(
        db, request.game_name, current_user.id
    )
    return GameDurationResponse(duration=duration if duration > 0 else None)
