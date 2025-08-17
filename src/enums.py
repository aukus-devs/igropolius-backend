from enum import Enum


class Role(Enum):
    PLAYER = "player"
    MODER = "moder"
    ADMIN = "admin"
    PRISON = "prison"


class PlayerTurnState(Enum):
    ROLLING_DICE = "rolling-dice"
    USING_DICE_BONUSES = "using-dice-bonuses"
    USING_PRISON_BONUSES = "using-prison-bonuses"
    ROLLING_BONUS_CARD = "rolling-bonus-card"
    FILLING_GAME_REVIEW = "filling-game-review"
    USING_MAP_TAX_BONUSES = "using-map-tax-bonuses"
    USING_STREET_TAX_BONUSES = "using-street-tax-bonuses"
    DROPPING_CARD_AFTER_GAME_DROP = "dropping-card-after-game-drop"
    DROPPING_CARD_AFTER_INSTANT_ROLL = "dropping-card-after-instant-roll"
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
    DROPPED = "dropped"
    STOLEN = "stolen"


class PlayerEventType(Enum):
    GAME = "game"
    BONUS_CARD = "bonus-card"
    SCORE_CHANGE = "score-change"
    PLAYER_MOVE = "player-move"


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
    INSTANT_CARD = "instant-card"


class BonusCardEventType(Enum):
    RECEIVED = "received"
    USED = "used"
    DROPPED = "dropped"
    STOLEN_FROM_ME = "stolen-from-me"
    STOLEN_BY_ME = "stolen-by-me"


class GameCompletionType(Enum):
    COMPLETED = "completed"
    DROP = "drop"
    REROLL = "reroll"


class StreamPlatform(Enum):
    TWITCH = "twitch"
    VK = "vk"
    KICK = "kick"
    NONE = "none"


class NotificationType(Enum):
    IMPORTANT = "important"
    STANDARD = "standard"


class NotificationEventType(Enum):
    GAME_COMPLETED = "game-completed"
    GAME_REROLL = "game-reroll"
    GAME_DROP = "game-drop"
    PAY_SECTOR_TAX = "pay-sector-tax"
    BUILDING_INCOME = "building-income"
    PAY_MAP_TAX = "pay-map-tax"
    BONUS_INCREASE = "bonus-increase"
    CARD_STOLEN = "card-stolen"
    CARD_LOST = "card-lost"
    EVENT_ENDING_SOON = "event-ending-soon"
    MESSAGE = "message"


class InstantCardType(Enum):
    # 1 Сюрприз — в честь вашего дня рождения все другие игроки перечисляют вам очки (3 от каждого).
    RECEIVE_1_PERCENT_FROM_ALL = "receive-1-percent-from-all"
    # 2 Выбыл, говорите? — получите очки, равные вашему месту в таблице. В перый игровой день, пока места не распределены - получите (5) очков.
    RECEIVE_SCORES_FOR_PLACE = "receive-scores-for-place"
    # 3 Тогда бесплатный тостер — если вы находитесь на одном из трех последних мест, получите 8 очков, в противном случае - потеряйте 4 очка. В перый игровой день, пока места не распределены - получите (5) очков.
    RECEIVE_5_PERCENT_OR_REROLL = "receive-5-percent-or-reroll"
    # 4 Деньги то, видит Бог, небольшие — получите (4) очков. +
    # RECEIVE_3_PERCENT = "receive-3-percent"
    # 5 А вот это явно не моя проблема —  первые три места в таблице лидеров теряют (5, 4, 3) очков. В перый игровой день, пока места не распределены - получите (5) очков.
    LEADERS_LOSE_PERCENTS = "leaders-lose-percents"
    # 6 Просто мы нашли резинку — получите (10) очков.
    RECEIVE_1_PERCENT_PLUS_20 = "receive-1-percent-plus-20"
    # 7 Он собирает установку — плюс один тир следующего здания.
    UPGRADE_NEXT_BUILDING = "upgrade-next-building"
    # 8 Я не мог просчитаться — минус один тир следующего здания.
    DOWNGRADE_NEXT_BUILDING = "downgrade-next-building"
    # 9 Плата? — потеряйте (4) очков.
    LOSE_2_PERCENTS = "lose-2-percents"
    # 10 Вернуться к исходной стадии — реролл этого колеса.
    REROLL = "reroll"
    # 11 Процесс стабилизируется — реролл этого колеса, плюс один дополнительный ролл.
    REROLL_AND_ROLL = "reroll-and-roll"
    # 12 Просто не повезло — потеряйте случайную карточку; если карточек нет, потеря (6) очков.
    LOSE_CARD_OR_3_PERCENT = "lose-card-or-3-percent"
    # 13 Коллекционер — получите количество очков, равное удвоенному количеству ваших карточек. Если карточек нет - реролл колеса.
    RECEVIE_SCORES_FOR_ACTIVE_CARDS = "receive-scores-for-active-cards"

    INCREASE_DIFFICULTY = "increase-difficulty"
    DECREASE_DIFFICULTY = "decrease-difficulty"

    # Аскет - если у вас меньше трех (<3) карт бонусов, получите 6х1 очков, в противном случае потеряйте 2х1 за каждую карту, начиная с третьей (если карт всего 3, штраф за одну и тд).
    ASKET = "asket"


class InstantCardResult(Enum):
    REROLL = "reroll"
    CARD_LOST = "card-lost"
    SCORE_CHANGE = "score-change"


class BonusCardType(Enum):
    ADJUST_BY_1 = "adjust-roll-by1"
    CHOOSE_1_DIE = "choose-1-die"
    SKIP_PRISON_DAY = "skip-prison-day"
    REROLL_GAME = "reroll-game"
    EVADE_STREET_TAX = "evade-street-tax"
    EVADE_MAP_TAX = "evade-map-tax"
    GAME_HELP_ALLOWED = "game-help-allowed"

    RECEIVE_1_PERCENT_FROM_ALL = "receive-1-percent-from-all"
    RECEIVE_SCORES_FOR_PLACE = "receive-scores-for-place"
    RECEIVE_5_PERCENT_OR_REROLL = "receive-5-percent-or-reroll"
    # RECEIVE_3_PERCENT = "receive-3-percent"
    LEADERS_LOSE_PERCENTS = "leaders-lose-percents"
    RECEIVE_1_PERCENT_PLUS_20 = "receive-1-percent-plus-20"
    UPGRADE_NEXT_BUILDING = "upgrade-next-building"
    DOWNGRADE_NEXT_BUILDING = "downgrade-next-building"
    LOSE_2_PERCENTS = "lose-2-percents"
    REROLL = "reroll"
    REROLL_AND_ROLL = "reroll-and-roll"
    LOSE_CARD_OR_3_PERCENT = "lose-card-or-3-percent"
    RECEVIE_SCORES_FOR_ACTIVE_CARDS = "receive-scores-for-active-cards"

    INCREASE_DIFFICULTY = "increase-difficulty"
    DECREASE_DIFFICULTY = "decrease-difficulty"
    ASKET = "asket"


class GameLength(Enum):
    EMPTY = ""
    TWO_TO_FIVE = "2-5"
    FIVE_TO_TEN = "5-10"
    TEN_TO_FIFTEEN = "10-15"
    FIFTEEN_TO_TWENTY = "15-20"
    TWENTY_TO_TWENTY_FIVE = "20-25"
    TWENTY_FIVE_PLUS = "25+"


class RulesCategory(Enum):
    GENERAL = "general"
    GAMEPLAY = "gameplay"
    DONATIONS = "donations"


class EventSetting(Enum):
    INSTANT_CARD_SCORE_MULTIPLIER = "instant_card_score_multiplier"
    EVENT_START_TIME = "event_start_time"
    EVENT_END_TIME = "event_end_time"
    ENDPOINT_RESET_DB_ENABLED = "endpoint_reset_db_enabled"


class GameDifficulty(Enum):
    EASY = -1
    NORMAL = 0
    HARD = 1
