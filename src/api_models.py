from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, field_validator
from typing_extensions import Literal

from src.enums import (
    BonusCardEventType,
    BonusCardType,
    GameCompletionType,
    GameDifficulty,
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
    status: GameCompletionType = Field(validation_alias="type")
    sector_id: int
    title: str = Field(validation_alias="item_title")
    review: str = Field(validation_alias="item_review")
    rating: float = Field(validation_alias="item_rating")
    length: GameLength = Field(validation_alias="item_length")
    length_bonus: int = Field(validation_alias="item_length_bonus")
    duration: int | None = None
    vod_links: str | None = None
    cover: str | None = None
    game_id: int | None = None
    difficulty_level: GameDifficulty
    score_change_amount: float | None = None
    player_sector_id: int


class ActiveBonusCard(BaseModel):
    bonus_type: MainBonusCardType
    received_at: int
    received_on_sector: int
    cooldown_turns_left: int


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
    sector_id: int
    total_score: float
    maps_completed: int
    games: list[PlayerGame]
    bonus_cards: list[ActiveBonusCard]
    color: str
    model_name: str
    building_upgrade_bonus: int
    game_difficulty_level: GameDifficulty


class PlayerListResponse(BaseModel):
    players: list[PlayerDetails]
    prison_cards: list[MainBonusCardType]


class BonusCardInfo(BaseModel):
    card_type: BonusCardType
    weight: float
    cooldown_turns: int


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
    bonus_cards: list[BonusCardInfo] = []


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
    instant_card_score_multiplier: float | None = None


class BonusCardEvent(PlayerEventBase):
    event_type: Literal["bonus-card"]
    subtype: BonusCardEventType
    bonus_type: BonusCardType | InstantCardType
    sector_id: int | None = None
    stolen_from_player: int | None = None
    stolen_by: int | None = None
    instant_card_score_multiplier: float | None = None


class GameEvent(PlayerEventBase):
    event_type: Literal["game"]
    subtype: GameCompletionType
    game_title: str
    game_cover: str | None = None
    sector_id: int
    player_sector_id: int


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
    game_id: int | None = None
    difficulty_level: GameDifficulty | None = None


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


class HltbGameResponse(BaseModel):
    game_id: int
    game_name: str
    game_name_date: int
    game_alias: str | None = None
    game_type: str
    game_image: str
    comp_lvl_combine: int
    comp_lvl_sp: int
    comp_lvl_co: int
    comp_lvl_mp: int
    comp_main: int
    comp_plus: int
    comp_100: int
    comp_all: int
    comp_main_count: int
    comp_plus_count: int
    comp_100_count: int
    comp_all_count: int
    invested_co: int
    invested_mp: int
    invested_co_count: int
    invested_mp_count: int
    count_comp: int
    count_speedrun: int
    count_backlog: int
    count_review: int
    review_score: int
    count_playing: int
    count_retired: int
    profile_platform: str | None = None
    profile_popular: int
    release_world: int | None = None
    genres: str | None = None
    steam_id: int | None = None
    description: str | None = None
    created_at: int
    updated_at: int


class HltbRandomGameRequest(BaseModel):
    min_length: int | None = None
    max_length: int | None = None
    limit: int = Field(default=12, ge=1, le=16)

    @field_validator("min_length", "max_length")
    @classmethod
    def validate_time_hours(cls, v):
        if v is not None and v < 0:
            raise ValueError("Time must be non-negative")
        return v

    @field_validator("max_length")
    @classmethod
    def validate_max_greater_than_min(cls, v, info):
        min_length = info.data.get("min_length")
        if min_length is not None:
            if v is None:
                raise ValueError(
                    "max_length must be specified when min_length is provided"
                )

            if min_length > 0 and v <= min_length:
                raise ValueError("max_length must be greater than min_length")
        return v


class HltbGamesListResponse(BaseModel):
    games: list[HltbGameResponse]


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
    endpoint_reset_db_enabled: int | None = None


class UpdatePlayerInternalRequest(BaseModel):
    player_id: int
    sector_id: int | None = None
    bonus_card: MainBonusCardType | None = None
    turn_state: PlayerTurnState | None = None


class EventSettingsResponse(BaseModel):
    settings: dict[str, str | None] = {}


class UseInstantCardRequest(BaseModel):
    card_type: InstantCardType
    card_to_lose: MainBonusCardType | None = None


class UseInstantCardResponse(BaseModel):
    result: InstantCardResult | None = None
    score_change: float | None = None


class GameDurationRequest(BaseModel):
    game_name: str


class GameDurationResponse(BaseModel):
    duration: int | None


class UpdatePlayerRequest(BaseModel):
    model_name: str
    color: str


class PlayerStats(BaseModel):
    player_id: int
    total_score: float
    username: str
    games_completed: int
    games_dropped: int
    score_from_games_completed: float
    score_from_games_dropped: float
    instant_cards_used: int
    score_from_cards: float
    score_lost_on_cards: float
    street_tax_paid: float
    map_tax_paid: float
    income_from_others: float


class PlayerStatsResponse(BaseModel):
    stats: list[PlayerStats]


class PlayerFinalStats(BaseModel):
    player_id: int
    username: str
    total_score: float
    games_completed: int
    games_dropped: int
    longest_game_hours: float
    shortest_game_hours: float
    cards_amount: int
    hours_played: float
    best_rated_game: PlayerGame | None = None
    worst_rated_game: PlayerGame | None = None


class FinalStatsResponse(BaseModel):
    total_score: float
    completed_games: int
    dice_rolls: int
    hours_spent_on_games: float
    cards_received: int
    cards_used: int
    maps_completed: int
    games_dropped: int
    games_rerolled: int
    train_rides: int
    average_rating_of_completed_games: float
    players: list[PlayerFinalStats]
