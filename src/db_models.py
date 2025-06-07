# models.py
from sqlalchemy import Integer, String, Float
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

from src.enums import PlayerTurnState
from src.utils.common import utc_now_ts

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nickname: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    url_handle: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_online: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_game: Mapped[str] = mapped_column(String, nullable=True)
    current_game_updated_at: Mapped[int] = mapped_column(Integer, nullable=True)
    online_count: Mapped[int] = mapped_column(Integer, default=0)
    current_auc_total_sum: Mapped[float] = mapped_column(Float, nullable=True)
    current_auc_started_at: Mapped[int] = mapped_column(Integer, nullable=True)
    pointauc_token: Mapped[str] = mapped_column(String, nullable=True)
    twitch_stream_link: Mapped[str] = mapped_column(String, nullable=True)
    vk_stream_link: Mapped[str] = mapped_column(String, nullable=True)
    kick_stream_link: Mapped[str] = mapped_column(String, nullable=True)
    telegram_link: Mapped[str] = mapped_column(String, nullable=True)
    donation_link: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=True)
    sector_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    turn_state: Mapped[str] = mapped_column(
        String, default=PlayerTurnState.INITIAL.value, nullable=False
    )
    last_dice_roll_id: Mapped[int] = mapped_column(Integer, nullable=True)
    maps_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PlayerGame(Base):
    __tablename__ = "player_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    updated_at: Mapped[int] = mapped_column(
        Integer, default=utc_now_ts, onupdate=utc_now_ts
    )
    duration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    item_title: Mapped[str] = mapped_column(String, nullable=False)
    item_review: Mapped[str] = mapped_column(String, nullable=False)
    item_rating: Mapped[float] = mapped_column(Integer, nullable=False)
    item_length: Mapped[str] = mapped_column(String, nullable=False)
    vod_links: Mapped[str] = mapped_column(String, nullable=True)
    sector_id: Mapped[int] = mapped_column(Integer, nullable=False)


class PlayerScoreChange(Base):
    __tablename__ = "player_score_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    updated_at: Mapped[int] = mapped_column(
        Integer, default=utc_now_ts, onupdate=utc_now_ts
    )
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    score_change: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    sector_id: Mapped[int] = mapped_column(Integer, nullable=False)


class PlayerCard(Base):
    __tablename__ = "player_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    updated_at: Mapped[int] = mapped_column(
        Integer, default=utc_now_ts, onupdate=utc_now_ts
    )
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    card_type: Mapped[str] = mapped_column(String, nullable=False)
    used_at: Mapped[int] = mapped_column(Integer, nullable=True)
    lost_at: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    received_on_sector: Mapped[int] = mapped_column(Integer, nullable=False)
    used_on_sector: Mapped[int] = mapped_column(Integer, nullable=True)
    lost_on_sector: Mapped[int] = mapped_column(Integer, nullable=True)


class PlayerMove(Base):
    __tablename__ = "player_moves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=utc_now_ts)
    updated_at: Mapped[int] = mapped_column(
        Integer, default=utc_now_ts, onupdate=utc_now_ts
    )
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    adjusted_roll: Mapped[int] = mapped_column(Integer, nullable=False)
    random_org_roll: Mapped[int] = mapped_column(Integer, nullable=False)
    sector_from: Mapped[int] = mapped_column(Integer, nullable=False)
    sector_to: Mapped[int] = mapped_column(Integer, nullable=False)
    move_type: Mapped[str] = mapped_column(String, nullable=False)
    map_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
