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
    USING_REROLL_BONUSES = "using-reroll-bonuses"
    FILLING_GAME_REVIEW = "filling-game-review"
    CHOOSING_TRAIN_RIDE = "choosing-train-ride"
    USING_MAP_TAX_BONUSES = "using-map-tax-bonuses"
    USING_STREET_TAX_BONUSES = "using-street-tax-bonuses"
    DROPPING_CARD_AFTER_GAME_DROP = "dropping-card-after-game-drop"
    DROPPING_CARD_AFTER_INSTANT_ROLL = "dropping-card-after-instant-roll"
    ENTERING_PRISON = "entering-prison"
    STEALING_BONUS_CARD = "stealing-bonus-card"
    CHOOSING_BUILDING_SECTOR = "choosing-building-sector"
    USING_MAP_TAX_BONUSES_AFTER_TRAIN_RIDE = "using-map-tax-bonuses-after-train-ride"


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
    INSTANT_CARD = "instant-card"


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
    # 1 Сюрприз — в честь вашего дня рождения все другие игроки перечисляют вам очки (1% от суммы каждого). +
    RECEIVE_1_PERCENT_FROM_ALL = "receive-1-percent-from-all"
    # 2 Выбыл, говорите? — получаете % очков, равный вашему месту в таблице. +
    RECEIVE_SCORES_FOR_PLACE = "receive-scores-for-place"
    # 3 Тогда бесплатный тостер — если вы находитесь во второй половине таблицы лидеров, получаете (5%) очков; если в первой - реролл колеса. +
    RECEIVE_5_PERCENT_OR_REROLL = "receive-5-percent-or-reroll"
    # 4 Деньги то, видит Бог, небольшие — получите (3%) очков. +
    RECEIVE_3_PERCENT = "receive-3-percent"
    # 5 А вот это явно не моя проблема —  первые три места в таблице лидеров теряют (3, 2, 1)% очков. +
    LEADERS_LOSE_PERCENTS = "leaders-lose-percents"
    # 6 Просто мы нашли резинку — получите (1%+20) очков. +
    RECEIVE_1_PERCENT_PLUS_20 = "receive-1-percent-plus-20"
    # 7 Он собирает установку — плюс один тир следующего здания.
    UPGRADE_NEXT_BUILDING = "upgrade-next-building"
    # 8 Я не мог просчитаться — минус один тир следующего здания.
    DOWNGRADE_NEXT_BUILDING = "downgrade-next-building"
    # 9 Плата? — потеряйте (2%) очков. +
    LOSE_2_PERCENTS = "lose-2-percents"
    # 10 Вернуться к исходной стадии — реролл этого колеса. +
    REROLL = "reroll"
    # 11 Процесс стабилизируется — реролл этого колеса, плюс один дополнительный ролл.
    REROLL_AND_ROLL = "reroll-and-roll"
    # 12 — игрок теряет случайную карточку; если карточек нет, потеря 3% очков. +
    LOSE_CARD_OR_3_PERCENT = "lose-card-or-3-percent"


class InstantCardResult(Enum):
    REROLL = "reroll"
    CARD_LOST = "card-lost"
    SCORES_RECEIVED = "score-received"
    SCORES_LOST = "scores-lost"


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
    RECEIVE_3_PERCENT = "receive-3-percent"
    LEADERS_LOSE_PERCENTS = "leaders-lose-percents"
    RECEIVE_1_PERCENT_PLUS_20 = "receive-1-percent-plus-20"
    UPGRADE_NEXT_BUILDING = "upgrade-next-building"
    DOWNGRADE_NEXT_BUILDING = "downgrade-next-building"
    LOSE_2_PERCENTS = "lose-2-percents"
    REROLL = "reroll"
    REROLL_AND_ROLL = "reroll-and-roll"
    LOSE_CARD_OR_3_PERCENT = "lose-card-or-3-percent"
