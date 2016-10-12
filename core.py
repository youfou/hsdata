#!/usr/bin/env python3
# coding: utf-8

"""
核心模块，包含基础的 Card、Deck、Data 类，以及一些周边的函数
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import json
import logging
import re
from collections import Counter

import requests

logging.basicConfig(level=logging.INFO)


DEFAULT_DATA_JSON_PATH = 'data/data.json'
DEFAULT_RESULTS_JSON_PATH = 'data/results.json'


"""
职业列表(dict)
key 为职业ID，value 为当前职业的关键词元组，其中第一个为职业名称，其余为可用于搜索的关键词
"""
CAREERS = {
    1: ('战士', '战', 'zhanshi', 'zs', 'zhan'),
    2: ('萨满', '萨', 'saman', 'sm', 'sa'),
    3: ('潜行者', '潜行', '潜', 'qianxingzhe', 'qxz', 'qianxing', 'qx', 'qian'),
    4: ('圣骑士', '圣骑', '圣', '骑', 'shengqishi', 'sqs', 'shengqi', 'sq', 'sheng', 'qi'),
    5: ('猎人', '猎', 'lieren', 'lr', 'lie'),
    6: ('德鲁伊', '德', '鲁', '伊', 'deluyi', 'dly', 'de', 'lu', 'yi'),
    7: ('术士', '术', 'shushi', 'ss', 'shu'),
    8: ('法师', '法', 'fashi', 'fs', 'fa'),
    9: ('牧师', '牧', 'mushi', 'ms', 'mu'),
}


def career_id_to_name(career_id):
    """
    职业ID转名称
    :param career_id: 职业ID
    :return: 职业名称
    """

    row = CAREERS.get(career_id)
    if row:
        return row[0]


def career_name_to_id(career_name):
    """
    职业名称转ID，名称可使用关键词
    :param career_name: 职业名称或关键词
    :return: 职业ID
    """

    for career_id, row in CAREERS.items():
        for word in row:
            if word in career_name.lower():
                logging.debug('Career: {}'.format(row[0]))
                return career_id


def class_to_career_id(class_id):
    """
    class是另一种职业ID分布标准，可需要的时候做转换
    :param class_id: class ID
    :return: 对应的职业ID
    """

    class_map = {
        2: 6, 3: 5, 4: 8,
        5: 4, 6: 9, 7: 3,
        8: 2, 9: 7, 10: 1,
    }

    if class_id is not None:
        return class_map.get(class_id)


"""用于保存读取到的卡组实战结果数据"""
DECK_RESULTS = None


def get_result(key, results_path):
    global DECK_RESULTS
    if DECK_RESULTS is None:
        with open(results_path, 'r') as fp:
            DECK_RESULTS = json.load(fp)

    return DECK_RESULTS.get(key)


class Card(object):
    """卡牌类"""

    def __init__(
            self,
            card_id='', name='', card_set=0, career_id=0, description='',
            cost=0, rarity=0, score=0, recommend='',
            arena_played=0, arena_won=0, arena_picked=None):
        # HSCARDS

        # dict key
        self.card_id = card_id
        # name_cn
        self.name = name
        # CardSet
        self.card_set = card_set
        # class -> career_id
        self.career_id = career_id
        # description_cn
        self.description = description
        # Cost
        self.cost = cost
        # Rarity
        self.rarity = rarity
        # score
        self.score = score
        # recommend
        self.recommend = recommend
        # arena_cout
        self.arena_played = arena_played
        # arena_win
        self.arena_won = arena_won
        # arena_hero
        self._arena_picked = arena_picked or dict()
        self._arena_picked = {int(k): int(v) for k, v in self._arena_picked.items()}

    def arena_picked(self, career_id):
        return self._arena_picked.get(career_id, 0)

    @property
    def arena_win_rate(self):
        if self.arena_played:
            return self.arena_won / self.arena_played

    def __repr__(self):
        return '<Card {}({})>'.format(self.name, self.card_id)

    def to_dict(self):
        return dict(
            card_id=self.card_id,
            name=self.name,
            card_set=self.card_set,
            career_id=self.career_id,
            description=self.description,
            cost=self.cost,
            rarity=self.rarity,
            score=self.score,
            recommend=self.recommend,
            arena_played=self.arena_played,
            arena_won=self.arena_won,
            arena_picked=self._arena_picked,
        )

    # for fp-growth

    def __eq__(self, other):
        return self.card_id == other.card_id

    def __gt__(self, other):
        return self.cost > other.cost

    def __ge__(self, other):
        return self.cost >= other.cost

    def __lt__(self, other):
        return self.cost < other.cost

    def __le__(self, other):
        return self.cost <= other.cost

    def __hash__(self):
        return hash('<__hs_card__: name="{}", id="{}">'.format(self.name, self.card_id))


class Deck(object):
    """卡组类"""

    def __init__(
            self,
            name='', mode='', career_id=0,
            cards=None, high_values=None,
            url='', tags=None, created_at='',
            heat=0, key='',
            results_path=DEFAULT_RESULTS_JSON_PATH
    ):
        self.results_path = results_path

        # pm20835

        # title
        self.name = name
        # game_mode
        self.mode = mode
        # job
        self.career_id = career_id
        # deckString > toPage
        self.cards = Counter(cards) or Counter()
        # deckString > deckKey
        self.high_values = high_values or list()
        # jump_url
        self.url = url
        # tag
        self.tags = tags or list()
        # time
        self.created_at = created_at
        # pm19022 > id > sl
        # self.win_rate = win_rate
        # pm19022 > id > hot
        self.heat = heat
        # md5key
        self.key = key

        # property
        self._results = None

    @property
    def results(self):
        if self._results is None:
            self._results = get_result(self.key, self.results_path)
        return self._results

    @property
    def users(self):
        if self.results:
            return self.results.get('users', 0)

    @property
    def played(self):
        if self.results:
            return self.results.get('offensive_count', 0) + self.results.get('subsequent_count', 0)

    @property
    def ranked_played(self):
        if self.results:
            return self.results.get('rank_count', 0)

    @property
    def won(self):
        if self.results:
            return self.results.get('offensive_win', 0) + self.results.get('subsequent_win', 0)

    @property
    def ranked_won(self):
        return self.results.get('rank_win', 0)

    @property
    def win_rate(self):
        if self.played:
            return self.won / self.played

    @property
    def ranked_win_rate(self):
        if self.ranked_played:
            return self.ranked_won / self.ranked_played

    def __repr__(self):
        return '<Deck: {}>'.format(self.name)

    def to_dict(self):
        return dict(
            name=self.name,
            mode=self.mode,
            career_id=self.career_id,
            cards=self.cards,
            high_values=self.high_values,
            url=self.url,
            tags=self.tags,
            created_at=self.created_at,
            heat=self.heat,
            key=self.key,
        )


class Data(object):
    """数据对象，可用于爬取、保存、载入数据，并提供了一些常用的方法"""

    def __init__(self, results_path=DEFAULT_RESULTS_JSON_PATH):

        self.results_path = results_path
        self.cards = {}
        self.decks = []
        self._jsons = {}

    @property
    def jsons(self):

        if not self._jsons:

            urls = (

                # 炉石盒子内嵌页面
                # http://hs.gameyw.netease.com/box_groups.html

                # HSCARDS: 卡牌信息(简略)
                # 'http://hsimg.gameyw.netease.com/static/inc/hscards.min.js',

                # HSCARDS: 卡牌信息
                'http://hsimg.gameyw.netease.com/static/inc/hscards.js',

                # pm20835: 卡组信息
                'http://hs.gameyw.netease.com/json/pm20835.js',

                # pm19022: 卡组热度和胜率
                'http://hsimg.gameyw.netease.com/pm19022.js',

                # pm20835_tag: tag信息
                # 'http://hs.gameyw.netease.com/json/pm20835_tag.js',
            )

            s = requests.Session()
            js_docs = []

            for url in urls:
                r = s.get(url)
                r.raise_for_status()
                js_docs.append(r.text)

            js_docs = '\n'.join(js_docs)
            m = re.findall(r'var\s+(\w+)\s*=\s*(.+);', js_docs)

            for var, value in m:
                self._jsons[var] = json.loads(value)

        return self._jsons

    @staticmethod
    def _get_num(parent, key_name, to_float=False):
        num = parent.get(key_name)
        if num == '':
            num = None
        if num is not None:
            if to_float:
                num = float(num)
            else:
                num = int(num)
        return num

    def _update_cards(self):
        for card_id, props in self.jsons['HSCARDS'].items():
            arena_picked = json.loads(props.get('arena_hero', '{}'))

            new_card = Card(
                card_id=card_id,
                name=props.get('name_cn'),
                card_set=self._get_num(props, 'CardSet'),
                career_id=class_to_career_id(self._get_num(props, 'Class')),
                description=props.get('description_cn'),
                cost=self._get_num(props, 'Cost'),
                rarity=self._get_num(props, 'Rarity'),
                score=self._get_num(props, 'score'),
                recommend=props.get('recommend'),
                arena_played=self._get_num(props, 'arena_cout'),
                arena_won=self._get_num(props, 'arena_win'),
                arena_picked=arena_picked
            )

            self.cards[card_id] = new_card

    def _update_decks(self):
        for deck in self.jsons['pm20835']:
            new_deck = Deck(
                name=deck.get('title'),
                mode=deck.get('game_mode'),
                career_id=self._get_num(deck, 'job'),
                url=deck.get('jump_url'),
                tags=deck.get('tag'),
                created_at=deck.get('time'),
                key=deck.get('md5key'),
            )

            new_deck.cards = Counter()
            for deck_card in deck['deckString']['toPage'].split(','):
                card_id, amount = deck_card.split(':')
                amount = int(amount)
                new_deck.cards[card_id] = amount

            new_deck.high_values = []
            for card_id in deck['deckString']['deckKey'].split(','):
                new_deck.high_values.append(card_id)

            ext = self.jsons['pm19022'].get(deck['md5key'])
            if ext:
                # new_deck.win_rate = self._get_num(ext, 'sl', to_float=True)
                new_deck.heat = self._get_num(ext, 'hot')

            self.decks.append(new_deck)

    def update(self, save_path=DEFAULT_DATA_JSON_PATH):
        """
        更新卡牌和卡组数据，但不包括卡组对战数据(需要另外使用scrapy爬取，见update_data.sh)
        :param save_path: 保存路径，若没有则不保存
        """

        self._update_cards()
        self._update_decks()
        if save_path:
            self.save(save_path)

    def save(self, path=DEFAULT_DATA_JSON_PATH):
        """
        保存爬取到的数据，方便下次直接载入
        :param path: 保存路径
        """

        save_cards = {}
        for card_id, card in self.cards.items():
            save_cards[card_id] = card.to_dict()
        save_decks = []
        for save_deck in self.decks:
            save_decks.append(save_deck.to_dict())

        with open(path, 'w') as fp:
            json.dump(dict(cards=save_cards, decks=save_decks), fp)

    def load(self, path=DEFAULT_DATA_JSON_PATH):
        """
        载入之前保存的数据
        :param path: 载入路径
        """

        with open(path, 'r') as fp:
            json_data = json.load(fp)

        self.cards = {}
        for card_id, props in json_data['cards'].items():
            self.cards[card_id] = Card(**props)

        self.decks = []
        for deck in json_data['decks']:
            self.decks.append(Deck(**deck))

    def search_decks(
            self,
            career_id=None,
            mode=None,
            min_win_rate=0.0,
            min_users=None,
            min_played=None,
            win_rate_top_n=None,
    ):
        """
        按特定条件搜索卡组
        :param career_id: 职业ID
        :param mode: 游戏模式，"标准" 或 "狂野"
        :param min_win_rate: 最低胜率，比如 0.6 表示 60%
        :param min_users: 最少使用用户数
        :param min_played: 最少使用次数
        :param win_rate_top_n: 根据胜率取 TOP N
        :return: 卡组列表
        """

        selected = []
        for deck in self.decks:

            results = deck.results

            if career_id and deck.career_id != career_id:
                continue
            elif mode and deck.mode != mode:
                continue
            elif min_win_rate and (deck.win_rate is None or deck.win_rate < min_win_rate):
                continue
            elif min_users:
                if not results:
                    continue
                elif deck.users < min_users:
                    continue
            elif min_played:
                if not results:
                    continue
                elif deck.played < min_played:
                    continue

            selected.append(deck)

            if win_rate_top_n:
                selected.sort(key=lambda x: x.win_rate, reverse=True)
                selected = selected[:win_rate_top_n]

        return selected

    def search_card(self, card_name, return_first=True):
        """
        根据名称搜索卡牌，可返回搜索到的第一个匹配卡牌或所有匹配卡牌
        :param card_name: 卡牌名称或关键词
        :param return_first: 选项，只返回找到的第一个卡牌或所有匹配卡牌
        :return: 根据 return_first 选项返回单个卡牌或卡牌列表，若没有匹配的卡牌则返回None
        """

        card_name = re.split(r'\W+', card_name)
        card_name = list(filter(lambda x: x, card_name))

        return_cards = []

        for card_id, card in self.cards.items():
            for w in card_name:
                if w not in card.name:
                    break
            else:
                if return_first:
                    logging.debug('{} found.'.format(card))
                    return card
                else:
                    return_cards.append(card)

        if not return_cards and return_first:
            return None
        else:
            return return_cards

    def card(self, card_id):
        """
        返回指定ID的卡牌对象
        :param card_id: 卡牌ID
        :return: 对应的卡牌对象
        """

        return self.cards.get(card_id)

    def card_stats(self, card_or_cards, decks, ranked_only=True):
        """
        在指定范围的卡组中对特定卡牌进行数据统计
        :param card_or_cards: 单卡(Card类)或多张卡牌(列表)
        :param decks: 卡组列表
        :param ranked_only: 选项，只看天梯数据
        :return: 统计结果，字典类型，若输入了多张卡，则为列表
        """

        if isinstance(card_or_cards, Card):
            cards = [card_or_cards]
        elif isinstance(card_or_cards, dict):
            cards = list()
            for k, v in card_or_cards.items():
                if isinstance(k, Card):
                    cards.append(k)
                elif isinstance(v, Card):
                    cards.append(v)
        elif isinstance(card_or_cards, list):
            cards = card_or_cards
        else:
            cards = list(card_or_cards)

        cards_ids = [card.card_id for card in cards]

        stats = {}

        for deck in decks:

            results = deck.results
            if not results:
                continue
            elif ranked_only and not deck.ranked_played:
                continue

            for card_id, card_count in deck.cards.items():

                card = self.card(card_id)

                if card.card_id not in cards_ids:
                    continue

                if card not in stats:
                    stats[card] = dict(
                        played=0,
                        won=0,
                        users=0,
                        used_in_decks=0,
                        total_count=0,
                        best_deck=None,
                    )

                if ranked_only:
                    stats[card]['played'] += deck.ranked_played
                    stats[card]['won'] += deck.ranked_won
                else:
                    stats[card]['played'] += deck.played
                    stats[card]['won'] += deck.won

                stats[card]['users'] += deck.users
                stats[card]['total_count'] += card_count
                stats[card]['used_in_decks'] += 1

                if not stats[card]['best_deck'] or deck.win_rate > stats[card]['best_deck'].win_rate:
                    stats[card]['best_deck'] = deck

        for card, stat in stats.items():
            stat['avg_win_rate'] = stat['won'] / stat['played']
            stat['avg_count'] = stat['total_count'] / stat['used_in_decks']

        if isinstance(card_or_cards, Card):
            return stats.get(card_or_cards, {})
        else:
            return stats

    def cost_curve(self, deck):
        """
        分析单个卡组的法力曲线
        :param deck: 卡组对象
        :return: 法力曲线，字典类型
        """

        curve = []
        for i in range(8):
            curve.append((i, 0))
        curve = dict(curve)

        for card_id, count in deck.cards.items():
            card = self.card(card_id)
            if card.cost >= 7:
                curve[7] += count
            else:
                curve[card.cost] += count

        return curve

    def avg_cost_curve(self, decks):
        """
        分析多个卡组的平均法力曲线
        :param decks: 卡组列表
        :return: 平均法力曲线，字典类型
        """

        curves = []
        for i in range(8):
            curves.append((i, []))
        curves = dict(curves)

        for deck in decks:
            for cost, count in self.cost_curve(deck).items():
                curves[cost].append(count)

        for cost, counts in curves.items():
            curves[cost] = sum(counts) / len(counts)

        return curves

    def similar_decks(self, deck, max_diff_count=3):
        """
        找到类似的卡组
        :param deck: 卡组对象
        :param max_diff_count: 最大卡牌差量，例如为3，则必须至少有27张相同的卡牌
        :return: 相似卡组列表，每个项为一个元组。其中第1项为卡组对象；第2项为差异描述字典
        """

        def convert_to_card(diff):
            new_diff = Counter()
            for card_id, count in diff.items():
                new_diff[self.card(card_id)] = count

            return new_diff

        ret = []

        for other_deck in self.decks:
            diff_1 = deck.cards - other_deck.cards
            diff_2 = other_deck.cards - deck.cards
            diff_count = len(list(diff_1.elements()))
            if diff_count <= max_diff_count:
                ret.append((
                    other_deck,
                    {
                        '+': convert_to_card(diff_1),
                        '-': convert_to_card(diff_2),
                        'diff_count': diff_count
                    }
                ))

        return ret


def career_converter(career, to='id'):
    """
    职业转换器
    :param career: 职业，可以是职业ID或关键词
    :param to: 目标类型，可以为'id'或'name'
    :return: 根据 to 参数返回所需的类型
    """

    if career:
        if isinstance(career, int):
            career_id = career
        else:
            career_id = career_name_to_id(career)

        if to == 'id':
            return career_id
        elif to == 'name':
            return career_id_to_name(career_id)
        else:
            raise Exception('Unknown "to type"')


def card_converter(card, to='obj', data=None):
    """
    卡牌转换器
    :param card: 卡牌，可以是卡牌对象或关键词，若为关键词则会在找到多张卡牌时抛出异常
    :param to: 目标类型，可以为 'obj', 'id', 或 'name'
    :param data: 引用的数据对象，若没有，会尝试载入，将消耗一定性能
    :return: 根据 to 参数返回所需的类型
    """

    if isinstance(card, Card):
        card_obj = card
    else:
        if not data:
            data = Data()
            data.load()
        card_obj = data.card(card)
        if not card_obj:
            cards_found = data.search_card(card, return_first=False)
            if cards_found and len(cards_found) == 1:
                card_obj = cards_found[0]
            elif cards_found:
                raise Exception('Multiple cards found.')
            else:
                card_obj = None

    logging.debug('{}'.format(card_obj))

    if to == 'obj':
        return card_obj
    elif to == 'id':
        if card_obj:
            return card_obj.card_id
    elif to == 'name':
        if card_obj:
            return card_obj.name
    else:
        raise Exception('Unknown "to type"')


if __name__ == '__main__':
    Data().update()
