from enum import Enum


class Role(Enum):
    PLAYER = "player"
    MODER = "moder"
    ADMIN = "admin"


class PlayerTurnState(Enum):
    ROLLING_DICE = "rolling-dice"
    USING_DICE_BONUSES = "using-dice-bonuses"
    USING_PRISON_BONUSES = "using-prison-bonuses"
    ROLLING_BONUS_CARD = "rolling-bonus-card"
    USING_REROLL_BONUSES = "using-reroll-bonuses"
    FILLING_GAME_REVIEW = "filling-game-review"
    CHOOSING_TRAIN_RIDE = "choosing-train-ride"
    USING_MAP_TAX_BONUSES = "using-map-tax-bonuses"
    USING_STREET_TAX_BONUSES = "using-street-tax-bonuses"
    ENTERING_PRISON = "entering-prison"
    STEALING_BONUS_CARD = "stealing-bonus-card"
    CHOOSING_BUILDING_SECTOR = "choosing-building-sector"


class MainBonusCardType(Enum):
    ADJUST_BY_1 = "adjust-roll-by1"
    CHOOSE_1_DIE = "choose-1-die"
    SKIP_PRISON_DAY = "skip-prison-day"
    REROLL_GAME = "reroll-game"
    EVADE_STREET_TAX = "evade-street-tax"
    EVADE_MAP_TAX = "evade-map-tax"
    GAME_HELP_ALLOWED = "game-help-allowed"


class BonusCardStatus(Enum):
    ACTIVE = "active"
    USED = "used"
    LOST = "lost"
    STOLEN = "stolen"


class PlayerMoveType(Enum):
    DICE_ROLL = "dice-roll"
    TRAIN_RIDE = "train-ride"
    DROP_TO_PRISON = "drop-to-prison"


class TaxType(Enum):
    STREET_TAX = "street-tax"
    MAP_TAX = "map-tax"


class ScoreChangeType(Enum):
    GAME_COMPLETED = "game-completed"
    GAME_DROPPED = "game-dropped"
    STREET_TAX = "street-tax"
    STREET_INCOME = "street-income"
    MAP_TAX = "map-tax"


class BonusCardEventType(Enum):
    RECEIVED = "received"
    USED = "used"
    LOST = "lost"
    STOLEN = "stolen"
    LOOTED = "looted"


class GameCompletionType(Enum):
    COMPLETED = "completed"
    DROP = "drop"
    REROLL = "reroll"


class StreamPlatform(Enum):
    TWITCH = "twitch"
    VK = "vk"
    KICK = "kick"
    NONE = "none"
