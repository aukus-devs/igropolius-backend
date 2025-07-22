import json
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_models import (
    ActiveBonusCard,
    BonusCardEvent,
    PlayerEventsResponse,
    GameEvent,
    PlayerMoveRequest,
    MoveEvent,
    SavePlayerGameRequest,
    SavePlayerGameResponse,
    ScoreChangeEvent,
    UpdatePlayerTurnStateRequest,
    PlayerGame as PlayerGameApiModel,
    PlayerListResponse,
    PlayerDetails,
)
from src.consts import GAME_LENGTHS_IN_ORDER, TRAIN_MAP
from src.db.db_models import (
    DiceRoll,
    EventSettings,
    IgdbGame,
    PlayerCard,
    PlayerGame as PlayerGameDbModel,
    PlayerMove,
    PlayerScoreChange,
    User,
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
    BonusCardType,
    GameCompletionType,
    MainBonusCardType,
    PlayerMoveType,
    ScoreChangeType,
)
from src.utils.auth import get_current_user_for_update
from src.utils.common import get_closest_prison_sector, map_bonus_card_to_event_type
from src.utils.db import utc_now_ts

router = APIRouter(tags=["players"])


@router.get("/api/players", response_model=PlayerListResponse)
async def get_users(db: Annotated[AsyncSession, Depends(get_db)]):
    users_query = await db.execute(select(User).filter(User.is_active == 1))
    users = users_query.scalars().all()
    games_query = await db.execute(select(PlayerGameDbModel))
    games = games_query.scalars().all()
    cards_query = await db.execute(
        select(PlayerCard).where(PlayerCard.status == "active")
    )
    cards = cards_query.scalars().all()

    event_settings_query = await db.execute(
        select(EventSettings).order_by(EventSettings.updated_at.desc()).limit(1)
    )
    event_settings = event_settings_query.scalars().first()

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
        model = PlayerDetails.model_validate(user)
        model.games = [
            PlayerGameApiModel(
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

    return {
        "players": users_models,
        "event_end_time": event_settings.event_end_time if event_settings else None,
        "event_start_time": event_settings.event_start_time if event_settings else None,
    }


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
    bonus_card_events = [
        BonusCardEvent(
            event_type="bonus-card",
            subtype=map_bonus_card_to_event_type(e),
            bonus_type=BonusCardType(e.card_type),
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
            event_type="score-change",
            subtype=ScoreChangeType(e.change_type),
            amount=e.score_change,
            reason=e.description,
            sector_id=e.sector_id,
            timestamp=e.created_at,
            score_before=e.score_before,
            score_after=e.score_after,
        )
        for e in score_changes
    ]
    all_events = move_events + game_events + bonus_card_events + score_change_events
    return {"events": all_events}


@router.post("/api/players/current/moves")
async def do_player_move(
    request: PlayerMoveRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    sector_id_from = current_user.sector_id

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
                choose_1_die_card.used_on_sector = sector_id_from

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
                adjust_by1_card.used_on_sector = sector_id_from

            if request.ride_train:
                train_target = TRAIN_MAP.get(current_user.sector_id)
                if not train_target:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Player must be on a train sector to use ride train option.",
                    )

                train_map_completed = current_user.sector_id > train_target
                train_move = PlayerMove(
                    player_id=current_user.id,
                    sector_from=current_user.sector_id,
                    sector_to=train_target,
                    move_type=PlayerMoveType.TRAIN_RIDE.value,
                    map_completed=train_map_completed,
                    adjusted_roll=10,
                    random_org_roll=-1,
                )
                db.add(train_move)
                current_user.sector_id = train_target
                if train_map_completed:
                    current_user.maps_completed += 1

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
    map_completed = False
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

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/player-games", response_model=SavePlayerGameResponse)
async def save_player_game(
    request: SavePlayerGameRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        game_duration = await calculate_game_duration_by_title(
            db, request.title, current_user.id
        )
    except Exception:
        game_duration = 0

    game = PlayerGameDbModel(
        player_id=current_user.id,
        type=request.status.value,
        item_title=request.title,
        item_review=request.review,
        item_rating=request.rating,
        item_length=request.length.value,
        vod_links=request.vod_links,
        sector_id=current_user.sector_id,
        game_id=request.game_id,
        duration=game_duration,
    )
    db.add(game)

    match request.status:
        case GameCompletionType.COMPLETED:
            # TODO move score calculation to backend
            await change_player_score(
                db,
                current_user,
                request.scores,
                ScoreChangeType.GAME_COMPLETED,
                f"game completed: '{request.title}'",
            )

            if game.item_length not in GAME_LENGTHS_IN_ORDER:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid game length: {game.item_length}. Must be one of {GAME_LENGTHS_IN_ORDER}.",
                )

            item_length_idx = GAME_LENGTHS_IN_ORDER.index(game.item_length)

            if (
                current_user.has_upgrade_bonus
                and item_length_idx != len(GAME_LENGTHS_IN_ORDER) - 1
            ):
                next_len = GAME_LENGTHS_IN_ORDER[item_length_idx + 1]
                game.item_length = next_len
                game.item_length_bonus = 1
                current_user.has_upgrade_bonus = False

            if current_user.has_downgrade_bonus and item_length_idx != 0:
                prev_len = GAME_LENGTHS_IN_ORDER[item_length_idx - 1]
                game.item_length = prev_len
                game.item_length_bonus = -1
                current_user.has_downgrade_bonus = False

    current_user.current_game = None
    current_user.current_game_updated_at = None
    current_user.current_game_cover = None
    await save_category_history(db, current_user.id, "NewPlayerGame")

    match request.status:
        case GameCompletionType.COMPLETED:
            await create_game_completed_notification(
                db, current_user.id, request.scores, request.title
            )
        case GameCompletionType.REROLL:
            await create_game_reroll_notification(db, current_user.id, request.title)
        case GameCompletionType.DROP:
            await create_game_drop_notification(db, current_user.id, request.title)

    return {"new_sector_id": current_user.sector_id}


@router.post("/api/players/current/turn-state")
async def update_turn_state(
    request: UpdatePlayerTurnStateRequest,
    current_user: Annotated[User, Depends(get_current_user_for_update)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user.turn_state = request.turn_state.value
    return Response(status_code=status.HTTP_204_NO_CONTENT)
