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
from datetime import datetime

import requests

DATA_DIR = 'data'

MODE_STANDARD = 'STANDARD'
MODE_WILD = 'WILD'

DATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

SOURCE_URL_CARDS = 'https://api.hearthstonejson.com/v1/'

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
        return Careers.CAREER_HEROES.get(self.class_name)

    def __repr__(self):
        return '<{}: {} ({})>'.format(
            self.__class__.__name__,
            self.name,
            self.class_name)

    def __eq__(self, other):
        return self.class_name == other.class_name


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
        CARDS.load_if_empty()
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

        self.career = None

    def __repr__(self):
        return '<{}: {} ({})>'.format(self.__class__.__name__, self.name, self.id)

    def __eq__(self, other):
        return self.id.lower() == other.id.lower()

    def __hash__(self):
        return hash('<__hs_card__: name="{}", id="{}">'.format(self.name, self.id))


class Cards(list):
    """
    卡牌合集，附带一些实用的方法
    """

    def __init__(self, json_path=None, update_if_not_found=True):
        """
        :param json_path: 读取或保存的JSON路径
        :param update_if_not_found: 选项，若上述文件不存在，则自动更新
        """
        super(Cards, self).__init__()

        if not json_path:
            json_path = os.path.join(DATA_DIR, JSON_FILE_NAME_CARDS)
        self.json_path = json_path

        self._index = dict()

        self.update_if_not_found = update_if_not_found

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

            card.career = CAREERS.get(data['playerClass'])
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
            r = s.get(SOURCE_URL_CARDS)
            r.raise_for_status()
            hs_version_codes = re.findall(r'href="/v1/(\d+)/all/"', r.text)
            hs_version_code = max(list(map(int, hs_version_codes)))
            logging.info('找到最新的对应炉石版本号: {}'.format(hs_version_code))

        json_url = '{}{}/{}/cards.json'.format(
            SOURCE_URL_CARDS, hs_version_code, MAIN_LANGUAGE)

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
            collectible=None, return_first=True
    ):
        """
        根据指定条件搜索卡牌
        :param in_name: 名称关键词
        :param in_text: 卡牌描述关键词
        :param career: 对应职业
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
            if isinstance(career, str):
                career = CAREERS.search(career)
                if not career:
                    raise Exception('Unknown career')

        found = None if return_first else list()

        for card in self:
            if name_keywords and not _all_keywords_in_text(name_keywords, card.name or ''):
                continue
            elif text_keywords and not _all_keywords_in_text(text_keywords, card.text or ''):
                continue
            elif career and not card.career == career:
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

    def __init__(self):
        self.name = None
        self.id = None

        self.career = None
        self.mode = None
        self.cards = Counter()

        self.updated_at = None
        self.url = None

        self.games = None
        self.wins = None
        self.draws = None

    @property
    def win_rate(self):
        if self.games:
            return self.wins / self.games

    @property
    def losses(self):
        if self.games:
            return self.games - (self.wins or 0) - (self.draws or 0)

    def to_dict(self):
        """
        用于保存为JSON
        :return 字典对象
        """
        dct = deepcopy(self.__dict__)
        dct['career'] = self.career.class_name
        dct['updated_at'] = self.updated_at.strftime(DATE_TIME_FORMAT)

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
        updated_at = dct.pop('updated_at', '')
        cards_dict = dct.pop('cards', dict())

        self.career = CAREERS.get(class_name)
        self.updated_at = datetime.strptime(updated_at, DATE_TIME_FORMAT)

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

    def __init__(self, json_path=None, update_if_not_found=True, cards=None):
        """
        :param cards: Cards 对象，用于将卡组内的卡牌ID转化为Card对象
        """
        super(Decks, self).__init__()

        self.source = self.deck_class.source

        if not json_path:
            json_path = os.path.join(DATA_DIR, 'DECKS_{}.json'.format(self.source))

        self.json_path = json_path
        self.update_if_not_found = update_if_not_found

        if not cards:
            cards = CARDS
        self.cards = cards
        self._index = dict()

        self.load(self.json_path)

    def append(self, deck):
        self._index[deck.id] = deck
        return super(Decks, self).append(deck)

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
            else:
                logging.warning('未找到卡牌数据，请使用 {}().update() 获取最新的数据'.format(
                    self.__class__.__name__))
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
            mode=None,
            min_win_rate=0.0,
            min_users=0,
            min_games=0,
            win_rate_top_n=None,
    ):
        if isinstance(career, str):
            career = CAREERS.search(career)

        def match(deck):
            if (not career or deck.career == career) \
                    and (not mode or deck.mode == mode) \
                    and ((deck.win_rate or 0.0) >= min_win_rate) \
                    and ((deck.users or 0) >= min_users) \
                    and ((deck.games or 0) >= min_games):
                return True

        found = list(filter(match, self))

        if win_rate_top_n:
            found.sort(key=lambda x: x.win_rate or 0, reverse=True)
            found = found[:win_rate_top_n]

        return found


with open(os.path.join(PACKAGE_DIR, 'career_names.json')) as fp:
    CAREER_NAMES_ALL_LANGUAGES = json.load(fp)


def set_data_dir(path):
    global DATA_DIR, CARDS
    DATA_DIR = path
    CARDS = Cards()


def set_main_language(language):
    """
    设置主要语言，包括职业和卡牌的描述文本
    Set main language, including description texts for Career and Card objects
    :param language: deDE, enUS, esES, esMX, frFR, itIT, jaJP, koKR, plPL, ptBR, ruRU, thTH, zhCN, zhTW
    """

    global MAIN_LANGUAGE, JSON_FILE_NAME_CARDS, CAREER_NAMES, CAREERS, CARDS

    CAREER_NAMES = CAREER_NAMES_ALL_LANGUAGES.get(language)
    if not CAREER_NAMES:
        raise ValueError('language: should in {}'.format(
            ', '.join(CAREER_NAMES_ALL_LANGUAGES.keys())))

    MAIN_LANGUAGE = language
    JSON_FILE_NAME_CARDS = 'CARDS_{}.json'.format(language)
    CAREERS = Careers()
    CARDS = Cards()


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


MAIN_LANGUAGE = 'zhCN'
JSON_FILE_NAME_CARDS = 'CARDS_{}.json'.format(MAIN_LANGUAGE)
CAREER_NAMES = CAREER_NAMES_ALL_LANGUAGES.get(MAIN_LANGUAGE)

CAREERS = Careers()
CARDS = Cards()
