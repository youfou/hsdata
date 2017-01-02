#!/usr/bin/env python3
# coding: utf-8


"""
用数据玩炉石!
~~~~~~~~~~~~

快速收集和分析炉石传说的卡牌及卡组数据


快速上手:

    >>> import hsdata
    >>>
    >>> # 获取卡组数据
    >>> decks = hsdata.HSBoxDecks()
    >>> # 若未找到本地数据，会自动从网络获取
    >>> print('从炉石盒子获取到', len(decks), '个卡组数据！')
    >>>
    >>> # 更新卡组数据
    >>> # decks.update()
    >>>
    >>> # 搜索卡组
    >>> found = decks.search(
    >>>     career='萨满',
    >>>     mode=hsdata.MODE_STANDARD,
    >>>     min_games=10000,
    >>>     win_rate_top_n=5)
    >>> print('其中5个胜率最高的萨满卡组:')
    >>> for deck in found:
    >>>     print('{}: {} 场, {:.2%} 胜'.format(
    >>>         deck.name, deck.games, deck.win_rate))
    >>>
    >>> # 查看卡组中的卡牌
    >>> print('其中第一个卡组用了这些卡牌')
    >>> print(found[0].cards)

----

GitHub: https://github.com/youfou/hsdata

----

:copyright: (c) 2016 by Youfou.
:license: Apache 2.0, see LICENSE for more details.

"""

import logging

from .core import (
    Career, Careers, Card, Cards, Deck, Decks,
    MODE_STANDARD, MODE_WILD, CAREERS, CARDS,
    set_data_dir, set_main_language, get_career, days_ago
)
from .hearthstats import HearthStatsDeck, HearthStatsDecks
from .hsbox import HSBoxDeck, HSBoxDecks
from .utils import (
    DeckGenerator,
    diff_decks, decks_expired, get_all_decks,
    cards_value, print_cards, cards_to_csv
)

logging.getLogger('scrapy').propagate = False
logging.getLogger('requests').propagate = False
logging.basicConfig(level=logging.INFO)

__title__ = 'hsdata'
__version__ = '0.2.15'
__author__ = 'Youfou'
__license__ = 'Apache 2.0'
__copyright__ = 'Copyright 2016 Youfou'
