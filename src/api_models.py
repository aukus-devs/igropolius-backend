from pydantic import BaseModel as PydanticBaseModel

from src.enums import (
    BonusCardEventType,
    GameCompletionType,
    MainBonusCardType,
    PlayerMoveType,
    PlayerTurnState,
    ScoreChangeType,
    StreamPlatform,
    TaxType,
)


class BaseModel(PydanticBaseModel):
    model_config = {
        "from_attributes": True,
    }


class UserGame(BaseModel):
    created_at: int
    status: GameCompletionType
    sector_id: int
    title: str
    review: str
    rating: float
    length: str
    duration: int | None = None
    vod_links: str | None = None
    cover: str | None = None


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
    current_game_cover: str | None = None
    current_game_updated_at: int | None = None
    current_game_duration: int | None = None
    online_count: int = 0
    current_auc_total_sum: float | None = None
    current_auc_started_at: int | None = None
    pointauc_token: str | None = None
    main_platform: StreamPlatform = StreamPlatform.NONE
    twitch_stream_link: str | None = None
    vk_stream_link: str | None = None
    kick_stream_link: str | None = None
    telegram_link: str | None = None
    donation_link: str | None = None
    avatar_link: str | None = None
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
    maps_completed: int = 0
    roll_result: list[int] = []


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
    dice_roll_json: dict | None = None
    map_completed: bool
    bonuses_used: list[MainBonusCardType] = []


class ScoreChangeEvent(UserEventBase):
    event_type: str = "score-change"
    subtype: ScoreChangeType
    amount: float
    reason: str
    sector_id: int


class BonusCardEvent(UserEventBase):
    event_type: str = "bonus-card"
    subtype: BonusCardEventType
    bonus_type: MainBonusCardType
    sector_id: int
    used_at: int | None = None
    used_on_sector: int | None = None
    lost_at: int | None = None
    lost_on_sector: int | None = None
    stolen_at: int | None = None
    stolen_from_player: int | None = None
    stolen_by: int | None = None


class GameEvent(UserEventBase):
    event_type: str = "game"
    subtype: GameCompletionType
    game_title: str
    game_cover: str | None = None
    sector_id: int


class EventsList(BaseModel):
    events: list[GameEvent | BonusCardEvent | ScoreChangeEvent | MoveEvent] = []


class GiveBonusCard(BaseModel):
    bonus_type: MainBonusCardType


class UseBonusCard(BaseModel):
    bonus_type: MainBonusCardType


class MakePlayerMove(BaseModel):
    type: PlayerMoveType
    bonuses_used: list[MainBonusCardType] = []
    selected_die: int | None = None


class UpdatePlayerTurnState(BaseModel):
    turn_state: PlayerTurnState


class ChangePlayerScore(BaseModel):
    type: ScoreChangeType
    amount: float
    sector_id: int
    reason: str


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
    scores: float
    game_id: int | None = None


class SavePlayerGameResponse(BaseModel):
    new_sector_id: int


class EditPlayerGame(BaseModel):
    game_title: str
    game_review: str
    vod_links: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class RulesVersion(BaseModel):
    content: str
    created_at: int


class RulesResponse(BaseModel):
    versions: list[RulesVersion] = []


class PayTaxRequest(BaseModel):
    tax_type: TaxType


class IgdbGameSummary(BaseModel):
    id: int
    name: str
    cover: str | None = None
    release_year: int | None = None


class IgdbGamesList(BaseModel):
    games: list[IgdbGameSummary] = []


class IgdbGamesSearchRequest(BaseModel):
    query: str
    limit: int = 20


class StealBonusCardRequest(BaseModel):
    player_id: int
    bonus_type: MainBonusCardType


class StreamCheckResponse(BaseModel):
    success: bool
    stats: dict


class RollDiceRequest(BaseModel):
    num: int = 2
    min: int = 1
    max: int = 8


class RollDiceResponse(BaseModel):
    roll_id: int
    is_random_org_result: bool
    random_org_check_form: str | None = None
    data: list[int]
