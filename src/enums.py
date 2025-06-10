from enum import Enum


class PlayerTurnState(Enum):
    ROLLING_DICE = "rolling-dice"
    USING_DICE_BONUSES = "using-dice-bonuses"
    USING_SECTOR_BONUSES = "using-sector-bonuses"
    PLAYING_GAME = "playing-game"
    ROLLING_BONUS_CARD = "rolling-bonus-card"
    USING_REROLL_BONUSES = "using-reroll-bonuses"
    FILLING_GAME_REVIEW = "filling-game-review"
    CHOOSING_TRAIN_RIDE = "choosing-train-ride"


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


class PlayerMoveType(Enum):
    DICE_ROLL = "dice-roll"
    TRAIN_RIDE = "train-ride"


class ScoreChangeType(Enum):
    GAME_COMPLETED = "game-completed"
    GAME_DROPPED = "game-dropped"
    STREET_TAX = "street-tax"
    MAP_TAX = "map-tax"


class BonusCardEventType(Enum):
    RECEIVED = "received"
    USED = "used"
    LOST = "lost"


class GameCompletionType(Enum):
    COMPLETED = "completed"
    DROP = "drop"
    REROLL = "reroll"
