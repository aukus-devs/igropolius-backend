from pydantic import BaseModel as PydanticBaseModel
from typing_extensions import Literal

from src.enums import (
    BonusCardEventType,
    BonusCardType,
    GameCompletionType,
    GameLength,
    InstantCardResult,
    InstantCardType,
    MainBonusCardType,
    NotificationEventType,
    NotificationType,
    PlayerMoveType,
    PlayerTurnState,
    Role,
    RulesCategory,
    ScoreChangeType,
    StreamPlatform,
    TaxType,
)


class BaseModel(PydanticBaseModel):
    model_config = {
        "from_attributes": True,
        "extra": "forbid",  # Disallow extra fields
    }


class PlayerGame(BaseModel):
    id: int
    player_id: int
    created_at: int
    status: GameCompletionType
    sector_id: int
    title: str
    review: str
    rating: float
    length: GameLength
    length_bonus: int | None = None
    duration: int | None = None
    vod_links: str | None = None
    cover: str | None = None


class ActiveBonusCard(BaseModel):
    bonus_type: MainBonusCardType
    received_at: int
    received_on_sector: int


class PlayerDetails(BaseModel):
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
    sector_id: int | None = None
    total_score: float | None = None
    maps_completed: int | None = None
    games: list[PlayerGame] | None = None
    bonus_cards: list[ActiveBonusCard] | None = None
    role: Role
    color: str | None = None
    model_name: str | None = None


class PlayerListResponse(BaseModel):
    players: list[PlayerDetails]


class CurrentUserResponse(BaseModel):
    id: int
    # url_handle: str
    username: str
    role: Role
    moder_for: int | None = None
    # sector_id: int
    # total_score: float = 0.0
    turn_state: PlayerTurnState | None = None
    # maps_completed: int = 0
    last_roll_result: list[int]
    has_upgrade_bonus: bool = False
    has_downgrade_bonus: bool = False


class PlayerEventBase(BaseModel):
    timestamp: int


class DiceRollDetails(BaseModel):
    is_random_org_result: bool
    random_org_check_form: str | None = None
    random_org_fail_reason: str | None = None
    data: list[int]


class MoveEvent(PlayerEventBase):
    event_type: Literal["player-move"]
    subtype: PlayerMoveType
    sector_from: int
    sector_to: int
    adjusted_roll: int
    dice_roll: list[int]
    dice_roll_json: DiceRollDetails | None
    map_completed: bool
    bonuses_used: list[MainBonusCardType]


class ScoreChangeEvent(PlayerEventBase):
    event_type: Literal["score-change"]
    subtype: ScoreChangeType
    amount: float
    reason: str
    sector_id: int
    score_before: float
    score_after: float
    income_from_player: int | None = None
    bonus_card: BonusCardType | None = None
    bonus_card_owner: int | None = None


class BonusCardEvent(PlayerEventBase):
    event_type: Literal["bonus-card"]
    subtype: BonusCardEventType
    bonus_type: BonusCardType | InstantCardType
    sector_id: int | None = None
    stolen_from_player: int | None = None
    stolen_by: int | None = None


class GameEvent(PlayerEventBase):
    event_type: Literal["game"]
    subtype: GameCompletionType
    game_title: str
    game_cover: str | None = None
    sector_id: int


class PlayerEventsResponse(BaseModel):
    events: list[GameEvent | BonusCardEvent | ScoreChangeEvent | MoveEvent]


class GiveBonusCardRequest(BaseModel):
    bonus_type: MainBonusCardType


class GiveBonusCardResponse(BaseModel):
    bonus_type: MainBonusCardType
    received_at: int
    received_on_sector: int


class UseBonusCard(BaseModel):
    bonus_type: MainBonusCardType


class PlayerMoveRequest(BaseModel):
    type: PlayerMoveType
    # bonuses_used: list[MainBonusCardType] = []
    selected_die: int | None = None
    adjust_by_1: int | None = None
    ride_train: bool = False


class PlayerMoveResponse(BaseModel):
    new_sector_id: int
    map_completed: bool


class UpdatePlayerTurnStateRequest(BaseModel):
    turn_state: PlayerTurnState


class DiceRollResult(BaseModel):
    roll_id: int
    dice: list[int]
    random_org_link: str | None = None


class SavePlayerGameRequest(BaseModel):
    status: GameCompletionType
    title: str
    review: str
    rating: float
    length: GameLength
    vod_links: str | None = None
    scores: float
    game_id: int | None = None


class SavePlayerGameResponse(BaseModel):
    new_sector_id: int


class MovePlayerGameRequest(BaseModel):
    new_sector_id: int


class EditPlayerGame(BaseModel):
    game_title: str
    game_review: str
    rating: float
    vod_links: str | None = None
    game_id: int | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str


class RulesVersion(BaseModel):
    content: str
    category: RulesCategory
    created_at: int


class NewRulesVersionRequest(BaseModel):
    content: str
    category: RulesCategory


class RulesResponse(BaseModel):
    versions: list[RulesVersion]


class PayTaxRequest(BaseModel):
    tax_type: TaxType


class IgdbGameSummary(BaseModel):
    id: int
    name: str
    cover: str | None = None
    release_year: int | None = None


class IgdbGamesListResponse(BaseModel):
    games: list[IgdbGameSummary]


class IgdbGamesSearchRequest(BaseModel):
    query: str
    limit: int = 20


class StealBonusCardRequest(BaseModel):
    player_id: int
    bonus_type: MainBonusCardType


class UseBonusCardRequest(BaseModel):
    bonus_type: MainBonusCardType


class DropBonusCardRequest(BaseModel):
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
    random_org_fail_reason: str | None = None


class NotificationItem(BaseModel):
    id: int
    notification_type: str
    event_type: NotificationEventType
    created_at: int
    other_player_id: int | None = None
    scores: float | None = None
    sector_id: int | None = None
    game_title: str | None = None
    card_name: str | None = None
    event_end_time: int | None = None
    message_text: str | None = None


class NotificationsResponse(BaseModel):
    notifications: list[NotificationItem]


class MarkNotificationsSeenRequest(BaseModel):
    notification_ids: list[int]


class CreateEventEndingNotificationRequest(BaseModel):
    event_end_time: int


class CreateAllPlayersNotificationRequest(BaseModel):
    notification_type: NotificationType
    event_type: NotificationEventType
    other_player_id: int | None = None
    scores: float | None = None
    sector_id: int | None = None
    game_title: str | None = None
    card_name: str | None = None
    event_end_time: int | None = None
    message_text: str | None = None


class CreatePlayerNotificationRequest(BaseModel):
    player_id: int
    notification_type: NotificationType
    event_type: NotificationEventType
    other_player_id: int | None = None
    scores: float | None = None
    sector_id: int | None = None
    game_title: str | None = None
    card_name: str | None = None
    event_end_time: int | None = None
    message_text: str | None = None


class CreateMessageNotificationRequest(BaseModel):
    notification_type: NotificationType
    message_text: str


class CreatePlayerMessageNotificationRequest(BaseModel):
    player_id: int
    notification_type: NotificationType
    message_text: str


class CreateNotificationResponse(BaseModel):
    success: bool
    message: str


class SetEventEndTimeRequest(BaseModel):
    event_start_time: int | None = None
    event_end_time: int | None = None


class EventSettingsResponse(BaseModel):
    settings: dict[str, str | None] = {}


class UseInstantCardRequest(BaseModel):
    card_type: InstantCardType
    card_to_lose: MainBonusCardType | None = None


class UseInstantCardResponse(BaseModel):
    result: InstantCardResult | None = None
