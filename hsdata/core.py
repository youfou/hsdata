#!/usr/bin/env python3
# coding: utf-8

"""
核心模块，包含所有基本类
~~~~~~~~~~~~~~~~~~~~~

包括:

* Career: 单个职业
* Careers: 职业合集，附带一些实用的方法
* Card: 单张卡牌
* Cards: 卡牌合集，附带一些实用的方法
* Deck: 单个卡组
* Decks: 卡组合集，附带一些实用的方法

"""

import json
import logging
import os
import re
import webbrowser
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta

import requests

DATA_DIR = 'data'

MODE_STANDARD = 'STANDARD'
MODE_WILD = 'WILD'

DATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

CARDS_SOURCE_URL = 'https://api.hearthstonejson.com/v1/'

PACKAGE_DIR = os.path.dirname(os.path.realpath(__file__))


class Career:
    def __init__(self, class_name):
        self.class_name = class_name

    @property
    def name(self):
        """
        获取当前职业在当前主语言中的名称
        :return: 职业名称
        """

        try:
            return CAREER_NAMES[self.class_name]
        except (TypeError, KeyError):
            return self.class_name

    @property
    def heroes(self):
        return Careers.CAREER_HEROES.get(self.class_name, list())

    def __repr__(self):
        return '<{}: {} ({})>'.format(
            self.__class__.__name__,
            self.name,
            self.class_name)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, Career):
            return self.class_name == other.class_name

    def __hash__(self):
        return hash('<__hsdata.Career__: class_name="{}">'.format(self.class_name))


class Careers(list):
    """
    职业合集，附带一些实用的方法
    """

    CLASS_NAMES = (
        'HUNTER', 'PRIEST', 'SHAMAN',
        'ROGUE', 'DRUID', 'PALADIN',
        'MAGE', 'WARRIOR', 'WARLOCK',
        'NEUTRAL',
        'DREAM',
    )

    # 各职业的英雄名称，将在 Cards.load() 时被添加
    CAREER_HEROES = dict()

    def __init__(self):
        super(Careers, self).__init__()

        self._index = dict()
        for class_name in self.CLASS_NAMES:
            career = Career(class_name)
            self.append(career)

    def append(self, career):
        self._index[career.class_name] = career
        return super(Careers, self).append(career)

    def clear(self):
        self._index.clear()
        return super(Careers, self).clear()

    def get(self, class_name):
        """
        根据 class_name 获取职业
        :param class_name: 可以理解为职业的 ID
        :return: 单个职业
        """
        return self._index.get(class_name)

    def search(self, keywords):
        """
        根据关键词搜索职业，将在 class_name，职业名称，英雄名称 中进行搜索
        :param keywords: 关键词，可以是列表或字串
        :return: 单个职业
        """

        if not keywords:
            return self.get('NEUTRAL')

        # 需要载入卡牌来填充各职业的英雄关键词
        CARDS.load_if_empty()

        if isinstance(keywords, str):
            keywords = _split_keywords(keywords)

        for career in self:
            if _all_keywords_in_text(keywords, career.class_name):
                return career

        for career in self:
            if _all_keywords_in_text(keywords, career.name):
                return career

        for career in self:
            for hero in career.heroes:
                if _all_keywords_in_text(keywords, hero):
                    return career

    @property
    def basic(self):
        return self[:9]


class Card:
    """单张卡牌"""

    def __init__(self):
        self.id = None
        self.type = None
        self.set = None
        self.name = None
        self.playerClass = None
        self.text = None
        self.cost = None
        self.rarity = None
        self.health = None
        self.attack = None
        self.artist = None
        self.collectible = None
        self.flavor = None
        self.mechanics = None
        self.dust = None
        self.playRequirements = None
        self.race = None
        self.howToEarnGolden = None
        self.howToEarn = None
        self.faction = None
        self.durability = None
        self.entourage = None
        self.targetingArrowText = None
        self.overload = None
        self.spellDamage = None
        # 201612: 加基森版本新增了3个字段
        self.classes = None
        self.multiClassGroup = None
        self.collectionText = None

    @property
    def career(self):
        return CAREERS.get(self.playerClass)

    @property
    def careers(self):
        if self.classes:
            return list(map(lambda x: CAREERS.get(x), self.classes))
        elif self.career:
            return [self.career]
        else:
            return list()

    def __repr__(self):
        return '<{}: {} ({})>'.format(self.__class__.__name__, self.name, self.id)

    def __eq__(self, other):
        return self.id.lower() == other.id.lower()

    def __hash__(self):
        return hash('<__hs.Card__: name="{}", id="{}">'.format(self.name, self.id))


class Cards(list):
    """
    卡牌合集，附带一些实用的方法
    """

    def __init__(self, json_path=None, update_if_not_found=True, lazy_load=False):
        """
        :param json_path: 读取或保存的JSON路径
        :param update_if_not_found: 选项，若上述文件不存在，则自动更新
        :param lazy_load: 选项，若为True，则在初始化时不载入实际数据，直到调用 get 或 search 方法
        """
        super(Cards, self).__init__()

        if not json_path:
            json_path = os.path.join(DATA_DIR, CARDS_JSON_FILE_NAME)
        self.json_path = json_path

        self._index = dict()

        self.update_if_not_found = update_if_not_found

        if not lazy_load:
            self.load()

    def append(self, card):
        self._index[card.id] = card
        return super(Cards, self).append(card)

    def clear(self):
        self._index.clear()
        return super(Cards, self).clear()

    def load_if_empty(self, json_path=None):
        """
        避免在模块初始化时执行载入(会产生文件)
        """
        if not self:
            self.load(json_path)

    def load(self, json_path=None):
        """
        载入本地的卡牌数据
        :param json_path: 文件路径
        """

        if not json_path:
            json_path = self.json_path

        if not os.path.isfile(json_path):
            if self.update_if_not_found:
                logging.info('未找到卡牌数据，将自动获取最新的数据')
                self.update(json_path)
            else:
                logging.warning('未找到卡牌数据，请使用 Cards().update() 获取最新的数据')
            return

        with open(json_path) as f:
            json_data = json.load(f)

        self.clear()

        logging.info('载入卡牌数据 {}'.format(json_path))

        for data in json_data:
            card = Card()

            for k, v in data.items():
                setattr(card, k, v)

            # HearthstoneJSON 中不可收集的卡牌没有设置 collectible 属性，添加该属性
            if card.collectible is None:
                card.collectible = False

            if card.type == 'HERO':
                # 将发现的英雄添加到 Careers.CAREER_HEROES 中
                if card.playerClass not in Careers.CAREER_HEROES:
                    Careers.CAREER_HEROES[card.playerClass] = list()
                if card.name not in Careers.CAREER_HEROES[card.playerClass]:
                    Careers.CAREER_HEROES[card.playerClass].append(card.name)

            self.append(card)

    def update(self, json_path=None, hs_version_code=None):
        """
        获取卡牌数据，保存为JSON，并返回一个新的 Cards 对象
        :param json_path: 保存路径
        :param hs_version_code: 炉石版本号，不填写则自动获取最新的
        :return: 新的 Cards 对象
        """

        if not json_path:
            json_path = self.json_path

        logging.info('开始更新卡牌数据，将保存到 {}'.format(json_path))
        s = requests.Session()

        if not hs_version_code:
            r = s.get(CARDS_SOURCE_URL)
            r.raise_for_status()
            hs_version_codes = re.findall(r'href="/v1/(\d+)/all/"', r.text)
            hs_version_code = max(list(map(int, hs_version_codes)))
            logging.info('找到最新的对应炉石版本号: {}'.format(hs_version_code))

        json_url = '{}{}/{}/cards.json'.format(
            CARDS_SOURCE_URL, hs_version_code, MAIN_LANGUAGE)

        logging.info('正在下载卡牌数据')
        r = s.get(json_url)
        r.raise_for_status()

        # 校验JSON
        r.json()

        _prepare_dir(json_path)

        with open(json_path, 'wb') as f:
            f.write(r.content)

        self.load(json_path)

        logging.info('卡牌数据更新完成')

    def get(self, card_id):
        """
        根据 ID 获取卡牌
        :param card_id: 卡牌 ID
        :return: 单张卡牌
        """
        self.load_if_empty()
        return self._index.get(card_id)

    def search(
            self,
            in_name=None, in_text=None, career=None,
            cost=None, collectible=None, return_first=True
    ):
        """
        根据指定条件搜索卡牌
        :param in_name: 名称关键词
        :param in_text: 卡牌描述关键词
        :param career: 对应职业
        :param cost: 卡牌的法力消耗值
        :param collectible: 是否可收集
        :param return_first: 选项，只返回首个匹配的卡牌
        :return: 根据 return_first 参数返回 单个职业/None 或 列表
        """

        self.load_if_empty()

        if in_name:
            name_keywords = _split_keywords(in_name)
        else:
            name_keywords = None

        if in_text:
            text_keywords = _split_keywords(in_text)
        else:
            text_keywords = None

        if career:
            career = get_career(career)

        found = None if return_first else list()

        for card in self:
            if name_keywords and not _all_keywords_in_text(name_keywords, card.name or ''):
                continue
            elif text_keywords and not _all_keywords_in_text(text_keywords, card.text or ''):
                continue
            elif career and not card.career == career:
                continue
            elif cost is not None and not card.cost == cost:
                continue
            elif collectible is not None and not card.collectible == collectible:
                continue
            else:
                if return_first:
                    return card
                else:
                    found.append(card)

        return found


class Deck:
    source = None
    DECK_URL_TEMPLATE = None

    def __init__(self):
        self.name = ''
        self.id = ''

        self.career = None
        self.cards = Counter()

        self.games = 0
        self.wins = 0
        self.draws = 0

    @property
    def win_rate(self):
        if self.games:
            return self.wins / self.games

    @property
    def losses(self):
        if self.games:
            return self.games - (self.wins or 0) - (self.draws or 0)

    @property
    def mode(self):
        for card in self.cards:
            if card.set in EXPIRED_SETS:
                return MODE_WILD
        else:
            return MODE_STANDARD

    @property
    def url(self):
        if self.id:
            return self.DECK_URL_TEMPLATE.format(self.id)

    @property
    def crafting_cost(self):
        dust = 0
        for card, count in self.cards.items():
            if card.dust:
                dust += card.dust[0] * count
        return dust

    def to_dict(self):
        """
        用于保存为JSON
        :return 字典对象
        """
        dct = deepcopy(self.__dict__)
        dct['career'] = self.career.class_name

        cards_dict = dict()
        for card, count in self.cards.items():
            cards_dict[card.id] = count
        dct['cards'] = cards_dict

        return dct

    def from_dict(self, dct, cards=None):
        """
        用于从JSON读取
        :param dct: 读取到的字典对象
        :param cards: 用于将卡牌ID转化为卡牌对象
        """

        class_name = dct.pop('career')
        cards_dict = dct.pop('cards', dict())
        self.career = CAREERS.get(class_name)

        if not cards:
            cards = CARDS

        for card_id, count in cards_dict.items():
            self.cards[cards.get(card_id)] = count

        for k, v in dct.items():
            setattr(self, k, v)

    def open(self):
        if self.url:
            webbrowser.open(self.url)
        else:
            logging.warning('无法在浏览器中打开{}，缺少URL'.format(self))

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.name)


class Decks(list):
    deck_class = Deck

    def __init__(
            self, deck_list=None, json_path=None, auto_load=False, update_if_not_found=True, cards=None):
        """
        :param deck_list: 一个 Deck 列表，用于直接转换为 Decks 对象
        :param cards: Cards 对象，用于将卡组内的卡牌ID转化为Card对象
        """
        super(Decks, self).__init__()

        self.source = self.deck_class.source

        self._index = dict()

        if deck_list:
            self.extend(deck_list)

        if not json_path:
            json_path = os.path.join(DATA_DIR, 'DECKS_{}.json'.format(self.source))

        self.json_path = json_path
        self.update_if_not_found = update_if_not_found

        if not cards:
            cards = CARDS
        self.cards = cards
        self.cards.load_if_empty()

        if auto_load:
            self.load(self.json_path)

    def append(self, deck):
        if not isinstance(deck, Deck):
            raise TypeError('{} 只能追加 Deck 对象'.format(self.__class__.__name__))
        self._index[deck.id] = deck
        return super(Decks, self).append(deck)

    def extend(self, decks):
        for deck in decks:
            if not isinstance(deck, Deck):
                raise TypeError('应为 Deck 对象，得到了 {}'.format(type(deck).__name__))
            self._index[deck.id] = deck
        return super(Decks, self).extend(decks)

    def remove(self, deck):
        del self._index[deck.id]
        return super(Decks, self).remove(deck)

    def clear(self):
        self._index.clear()
        return super(Decks, self).clear()

    def update(self, json_path=None):
        """
        从数据源获取卡组数据
        :param json_path: 保存路径
        """

        # 具体的获取过程由子类实现
        pass

    def save(self, json_path=None):
        """
        将卡组合集保存为JSON文件
        :param json_path: 保存路径
        """

        if not json_path:
            json_path = self.json_path

        save_list = list()

        for deck in self:
            save_list.append(deck.to_dict())

        _prepare_dir(json_path)
        with open(json_path, 'w') as f:
            json.dump(save_list, f, ensure_ascii=False)

        logging.info('已保存到 {}'.format(json_path))

    def load(self, json_path=None):
        """
        从JSON文件中载入卡组合集
        :param json_path: JSON文件路径
        """

        if not json_path:
            json_path = self.json_path

        if not os.path.isfile(json_path):
            if self.update_if_not_found:
                logging.info('未找到卡组数据，将自动获取最新的数据')
                self.update(json_path)
            return

        logging.info('载入卡组数据 {}'.format(json_path))

        with open(json_path) as f:
            data_list = json.load(f)

        self.clear()
        for deck_dict in data_list:
            deck = self.deck_class()
            deck.from_dict(deck_dict, self.cards)
            self.append(deck)

    def get(self, deck_id):
        return self._index.get(deck_id)

    def search(
            self,
            career=None,
            mode=MODE_STANDARD,
            min_win_rate=0.0,
            min_games=0,
            win_rate_top_n=None,
    ):
        """
        在当前卡组合集中搜索符合条件的卡组
        :param career: 职业
        :param mode: 模式，可以是 MODE_STANDARD 或 MODE_WILD
        :param min_win_rate: 最低胜率
        :param min_games: 最少游戏次数
        :param win_rate_top_n: 将结果按胜率倒排，并截取其中的前 n 个，若为负数则返回所有卡组
        :return: 符合条件的卡组列表
        """

        if career:
            career = get_career(career)

        def match(deck):
            if (not career or deck.career == career) \
                    and (not mode or deck.mode == mode) \
                    and ((deck.win_rate or 0) >= min_win_rate) \
                    and ((deck.games or 0) >= min_games):
                return True

        found = list(filter(match, self))

        if win_rate_top_n:
            found.sort(key=lambda x: x.win_rate or 0, reverse=True)
            if win_rate_top_n > 0:
                found = found[:win_rate_top_n]

        return Decks(found)

    @property
    def total_games(self):
        return sum(map(lambda x: x.games or 0, self))

    @property
    def total_wins(self):
        return sum(map(lambda x: x.wins or 0, self))

    @property
    def avg_win_rate(self):
        try:
            return self.total_wins / self.total_games
        except ZeroDivisionError:
            pass

    def career_cards_stats(
            self, career, mode=MODE_STANDARD,
            min_games=1000, top_win_rate_percentage=0.1
    ):
        """
        统计指定职业和模式的卡牌数据，可在组建卡组时作为参考
        1. 选取当前职业和模式中符合 top_win_rate_percentage, min_games 条件的所有卡组
        2. 选取上述卡组中所用到的卡牌
        3. 统计这些卡牌在上述卡组中的表现数据

        表现数据中包括
        avg_count: (在top_decks中的)平均使用数量
        avg_win_rate: 平均胜率(总胜率次数/总游戏次数)
        total_games: 总游戏次数
        used_in_decks: 用到该卡牌的卡组数

        :param career: 职业
        :param mode: 模式，可以是 MODE_STANDARD 或 MODE_WILD
        :param min_games: 最少游戏次数
        :param top_win_rate_percentage: 选取胜率最高的 n% 卡组，0.1 表示 10%
        """

        career = get_career(career)

        top_decks = self.search(
            career=career, mode=mode,
            min_games=min_games, win_rate_top_n=-1)
        top_decks = top_decks[:round(len(top_decks) * top_win_rate_percentage)]

        "total_count, total_games, total_wins, used_in_decks, avg_count, avg_win_rate"

        cards_stats = dict()
        for deck in top_decks:
            for card, count in deck.cards.items():
                if card not in cards_stats:
                    cards_stats[card] = dict(
                        total_count=0,
                        total_games=0,
                        total_wins=0,
                        used_in_decks=0,
                    )
                cards_stats[card]['used_in_decks'] += 1
                cards_stats[card]['total_count'] += count
                cards_stats[card]['total_games'] += deck.games or 0
                cards_stats[card]['total_wins'] += deck.wins or 0

        for card, stats in cards_stats.items():
            stats['avg_count'] = stats['total_count'] / stats['used_in_decks']
            if stats['total_games']:
                stats['avg_win_rate'] = stats['total_wins'] / stats['total_games']
            else:
                stats['avg_win_rate'] = None

        return cards_stats, top_decks

    def __getitem__(self, item):
        ret = super(Decks, self).__getitem__(item)
        if isinstance(item, slice):
            decks = Decks()
            decks.extend(ret)
            ret = decks
        return ret


with open(os.path.join(PACKAGE_DIR, 'career_names.json')) as fp:
    CAREER_NAMES_ALL_LANGUAGES = json.load(fp)


def set_data_dir(path):
    global DATA_DIR, CARDS
    DATA_DIR = path
    CARDS = Cards(lazy_load=True)


def set_main_language(language):
    """
    设置主要语言，包括职业和卡牌的描述文本
    Set main language, including description texts for Career and Card objects
    :param language: deDE, enUS, esES, esMX, frFR, itIT, jaJP, koKR, plPL, ptBR, ruRU, thTH, zhCN, zhTW
    """

    global MAIN_LANGUAGE, CARDS_JSON_FILE_NAME, CAREER_NAMES, CAREERS, CARDS

    CAREER_NAMES = CAREER_NAMES_ALL_LANGUAGES.get(language)
    if not CAREER_NAMES:
        raise ValueError('language: should in {}'.format(
            ', '.join(CAREER_NAMES_ALL_LANGUAGES.keys())))

    MAIN_LANGUAGE = language
    CARDS_JSON_FILE_NAME = 'CARDS_{}.json'.format(language)
    CAREERS = Careers()
    CARDS = Cards(lazy_load=True)


def _split_keywords(keywords):
    if isinstance(keywords, str):
        keywords = re.findall(r'\w+', keywords)
    return keywords


def _all_keywords_in_text(keywords, text):
    if isinstance(keywords, str):
        keywords = _split_keywords(keywords)
    for keyword in keywords:
        if keyword.lower() not in text.lower():
            return False
    else:
        return True


def _prepare_dir(path):
    file_dir = os.path.dirname(path)
    if file_dir:
        os.makedirs(file_dir, exist_ok=True)


def get_career(keywords_or_career=None):
    """
    获取指定职业(Career)对象
    :param keywords_or_career: 指定职业的关键词或Career对象
    :return: 职业(Career)对象
    """
    if isinstance(keywords_or_career, Career):
        career = keywords_or_career
    elif isinstance(keywords_or_career, (str, list, type(None))):
        career = CAREERS.search(keywords_or_career)
    else:
        raise TypeError('不支持使用 {} 作为参数'.format(
            type(keywords_or_career).__name__))

    return career


def days_ago(n):
    return datetime.today() - timedelta(days=n)


MAIN_LANGUAGE = 'zhCN'
CARDS_JSON_FILE_NAME = 'CARDS_{}.json'.format(MAIN_LANGUAGE)
CAREER_NAMES = CAREER_NAMES_ALL_LANGUAGES.get(MAIN_LANGUAGE)

CAREERS = Careers()
CARDS = Cards(lazy_load=True)

# 用于判断卡组模式：若卡组中包含已过期卡包的卡牌，则认为是狂野模式
# 这个列表需要跟随游戏不断更新！
EXPIRED_SETS = ('REWARD', 'NAXX', 'GVG', 'TB')
