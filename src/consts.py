from itertools import chain
from src.enums import GameLength


SCORES_BY_GAME_LENGTH = {
    GameLength.TWO_TO_FIVE.value: 10,
    GameLength.FIVE_TO_TEN.value: 20,
    GameLength.TEN_TO_FIFTEEN.value: 30,
    GameLength.FIFTEEN_TO_TWENTY.value: 40,
    GameLength.TWENTY_TO_TWENTY_FIVE.value: 50,
    GameLength.TWENTY_FIVE_PLUS.value: 60,
}

GAME_LENGTHS_IN_ORDER = list(SCORES_BY_GAME_LENGTH.keys())


STREET_INCOME_MULTILIER = 0.5
STREET_INCOME_GROUP_OWNER_MULTILIER = 0.8
STREET_TAX_PAYER_MULTILIER = 0.5

MAP_TAX_PERCENT = 0.1

TRAIN_MAP = {
    6: 16,
    16: 26,
    26: 36,
    36: 6,
}


SECTORS_COLORS_GROUPS = [
    [2, 4, 5],
    [7, 9, 10],
    [12, 14, 15],
    [17, 19, 20],
    [22, 24, 25],
    [27, 28, 30],
    [32, 33, 35],
    [37, 38, 40],
    list(TRAIN_MAP.keys()),
]


BUILDING_SECTORS = set(chain(chain.from_iterable(SECTORS_COLORS_GROUPS), [1]))
BONUS_SECTORS = {3, 8, 13, 18, 23, 29, 34, 39}
