from pydantic import BaseModel as PydanticBaseModel

from src.enums import (
    BonusCardEventType,
    GameCompletionType,
    MainBonusCardType,
    PlayerMoveType,
    PlayerTurnState,
    ScoreChangeType,
)


class BaseModel(PydanticBaseModel):
    model_config = {
        "from_attributes": True,
    }


class UserGame(BaseModel):
    sector_id: int
    game_title: str
    game_length: str
    created_at: int


class BonusCard(BaseModel):
    bonus_type: str
    received_at: int
    received_on_sector: int


class UserSummary(BaseModel):
    id: int
    username: str
    first_name: str
    url_handle: str
    is_online: bool
    current_game: str | None = None
    current_game_updated_at: int | None = None
    online_count: int = 0
    current_auc_total_sum: float | None = None
    current_auc_started_at: int | None = None
    pointauc_token: str | None = None
    twitch_stream_link: str | None = None
    vk_stream_link: str | None = None
    kick_stream_link: str | None = None
    telegram_link: str | None = None
    donation_link: str | None = None
    is_active: bool = True
    sector_id: int
    total_score: float = 0.0
    maps_completed: int
    games: list[UserGame] = []
    bonus_cards: list[BonusCard] = []


class UsersList(BaseModel):
    players: list[UserSummary] = []


class CurrentUser(BaseModel):
    id: int
    url_handle: str
    username: str
    moder_for: int | None = None
    sector_id: int
    total_score: float = 0.0
    turn_state: PlayerTurnState
    last_dice_roll_id: int | None = None
    last_dice_roll: list[int] | None = None
    maps_completed: int = 0


class UserEventBase(BaseModel):
    timestamp: int
    event_type: str


class MoveEvent(UserEventBase):
    event_type: str = "player-move"
    subtype: PlayerMoveType
    sector_from: int
    sector_to: int
    adjusted_roll: int
    dice_roll: list[int]
    map_completed: bool


class ScoreChangeEvent(UserEventBase):
    event_type: str = "score-changed"
    subtype: ScoreChangeType
    score_change: float
    reason: str
    sector_id: int


class BonusCardEvent(UserEventBase):
    event_type: str = "bonus-card"
    subtype: BonusCardEventType
    bonus_type: MainBonusCardType
    sector_id: int


class GameEvent(UserEventBase):
    event_type: str = "game"
    subtype: GameCompletionType
    game_title: str
    sector_id: int


class EventsList(BaseModel):
    events: list[GameEvent | BonusCardEvent | ScoreChangeEvent | MoveEvent] = []


class GiveBonusCard(BaseModel):
    bonus_type: MainBonusCardType


class UseBonusCard(BaseModel):
    bonus_type: MainBonusCardType


class MakePlayerMove(BaseModel):
    type: PlayerMoveType
    dice_roll_id: int | None = None
    bonuses_used: list[MainBonusCardType] = []
    selected_die: int | None = None
    tmp_roll_result: int


class UpdatePlayerTurnState(BaseModel):
    turn_state: PlayerTurnState


class ChangePlayerScore(BaseModel):
    type: ScoreChangeType
    amount: float
    sector_id: int
    tax_player_id: int | None = None


class DiceRollResult(BaseModel):
    roll_id: int
    dice: list[int]
    random_org_link: str | None = None


class SavePlayerGame(BaseModel):
    status: GameCompletionType
    title: str
    review: str
    rating: float
    length: str
    vod_links: str | None = None


class EditPlayerGame(BaseModel):
    game_title: str
    game_review: str
    vod_links: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str
