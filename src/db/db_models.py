# models.py
from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column  # pyright: ignore[reportAttributeAccessIssue]
from sqlalchemy.orm.decl_api import declarative_base

from src.enums import BonusCardStatus, PlayerTurnState, Role, StreamPlatform
from src.utils.db import utc_now_ts

DbBase = declarative_base()


class User(DbBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    url_handle: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(
        String(255), default=Role.PLAYER.value, nullable=False
    )
    is_online: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_game: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_game_cover: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_game_updated_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    online_count: Mapped[int] = mapped_column(Integer, default=0)
    current_auc_total_sum: Mapped[float] = mapped_column(Float, nullable=True)
    current_auc_started_at: Mapped[int] = mapped_column(Integer, nullable=True)
    pointauc_token: Mapped[str] = mapped_column(String(255), nullable=True)
    main_platform: Mapped[str] = mapped_column(
        String(255), default=StreamPlatform.NONE.value, nullable=False
    )
    twitch_stream_link: Mapped[str] = mapped_column(String(255), nullable=True)
    vk_stream_link: Mapped[str] = mapped_column(String(255), nullable=True)
    kick_stream_link: Mapped[str] = mapped_column(String(255), nullable=True)
    telegram_link: Mapped[str] = mapped_column(String(255), nullable=True)
    donation_link: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=True, index=True)
    avatar_link: Mapped[str] = mapped_column(String(255), nullable=True)
    sector_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    turn_state: Mapped[str] = mapped_column(
        String(255), default=PlayerTurnState.ROLLING_DICE.value, nullable=False
    )
    maps_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_upgrade_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_downgrade_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # default for pydantic conversions
    games = []
    bonus_cards = []
    last_roll_result = []


class PlayerGame(DbBase):
    __tablename__ = "player_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    updated_at: Mapped[int] = mapped_column(
        Integer, default=utc_now_ts, onupdate=utc_now_ts
    )
    duration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    item_title: Mapped[str] = mapped_column(String(255), nullable=False)
    item_review: Mapped[str] = mapped_column(Text, nullable=False)
    item_rating: Mapped[float] = mapped_column(Integer, nullable=False)
    item_length: Mapped[str] = mapped_column(String(255), nullable=False)
    vod_links: Mapped[str] = mapped_column(String(255), nullable=True)
    sector_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    game_id: Mapped[int] = mapped_column(Integer, nullable=True)
    item_length_bonus: Mapped[int] = mapped_column(Integer, nullable=True)
    player_sector_id: Mapped[int] = mapped_column(Integer, nullable=False)


class PlayerScoreChange(DbBase):
    __tablename__ = "player_score_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    updated_at: Mapped[int] = mapped_column(
        Integer, default=utc_now_ts, onupdate=utc_now_ts
    )
    player_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    score_change: Mapped[float] = mapped_column(Float, nullable=False)
    change_type: Mapped[str] = mapped_column(String(255), nullable=False)
    sector_id: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    score_before: Mapped[float] = mapped_column(Float, nullable=False)
    score_after: Mapped[float] = mapped_column(Float, nullable=False)
    income_from_player: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PlayerCard(DbBase):
    __tablename__ = "player_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    updated_at: Mapped[int] = mapped_column(
        Integer, default=utc_now_ts, onupdate=utc_now_ts
    )
    player_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    card_type: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(255), nullable=False, default=BonusCardStatus.ACTIVE.value, index=True
    )
    received_on_sector: Mapped[int] = mapped_column(Integer, nullable=False)
    used_at: Mapped[int] = mapped_column(Integer, nullable=True)
    used_on_sector: Mapped[int] = mapped_column(Integer, nullable=True)
    lost_at: Mapped[int] = mapped_column(Integer, nullable=True)
    lost_on_sector: Mapped[int] = mapped_column(Integer, nullable=True)
    stolen_at: Mapped[int] = mapped_column(Integer, nullable=True)
    stolen_by: Mapped[int] = mapped_column(Integer, nullable=True)
    stolen_from_player: Mapped[int] = mapped_column(Integer, nullable=True)
    player_move_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )


class PlayerMove(DbBase):
    __tablename__ = "player_moves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    updated_at: Mapped[int] = mapped_column(
        Integer, default=utc_now_ts, onupdate=utc_now_ts
    )
    player_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    adjusted_roll: Mapped[int] = mapped_column(Integer, nullable=False)
    random_org_roll: Mapped[int] = mapped_column(Integer, nullable=False)
    sector_from: Mapped[int] = mapped_column(Integer, nullable=False)
    sector_to: Mapped[int] = mapped_column(Integer, nullable=False)
    move_type: Mapped[str] = mapped_column(String(255), nullable=False)
    map_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Rules(DbBase):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts, index=True)
    updated_at: Mapped[int] = mapped_column(
        Integer, default=utc_now_ts, onupdate=utc_now_ts
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)


class IgdbGame(DbBase):
    __tablename__ = "igdb_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    cover: Mapped[str] = mapped_column(Text, nullable=True)
    release_year: Mapped[int] = mapped_column(Integer, nullable=True)


class CategoryHistory(DbBase):
    __tablename__ = "categories_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_name: Mapped[str] = mapped_column(String(255), nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    category_date: Mapped[int] = mapped_column(Integer, default=utc_now_ts)


class DiceRoll(DbBase):
    __tablename__ = "dice_rolls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_random_org_result: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    random_org_fail_reason: Mapped[str] = mapped_column(Text, nullable=True)
    json_short_data: Mapped[str] = mapped_column(Text, nullable=False)
    random_org_result: Mapped[str] = mapped_column(Text, nullable=True)
    dice_values: Mapped[str] = mapped_column(String(255), nullable=False)
    random_org_check_url: Mapped[str] = mapped_column(Text, nullable=True)


class ErrorLog(DbBase):
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    player_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    error_type: Mapped[str] = mapped_column(String(255), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    function_name: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)


class Notification(DbBase):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    is_read: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    other_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scores: Mapped[float | None] = mapped_column(Float, nullable=True)
    sector_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    game_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    card_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_end_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)


class EventSettings(DbBase):
    __tablename__ = "event_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    updated_at: Mapped[int] = mapped_column(
        Integer, default=utc_now_ts, onupdate=utc_now_ts
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
