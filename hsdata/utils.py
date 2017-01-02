#!/usr/bin/env python3
# coding: utf-8


"""
一些实用的小功能
"""
import csv
import logging
import os
from collections import Counter
from datetime import datetime, timedelta

from .core import (
    MODE_STANDARD,
    Decks,
    days_ago,
    Career, CAREERS, Cards)
from .hearthstats import HearthStatsDecks
from .hsbox import HSBoxDecks


def diff_decks(*decks):
    """
    卡组对比
    :param decks: 两个或以上的卡组
    :return: 返回每个卡组特有的部分
    """

    intersection = decks[0].cards & decks[1].cards
    for deck in decks[2:]:
        intersection &= deck.cards

    differs = dict(intersection=intersection)

    for deck in decks:
        differs[deck] = deck.cards - intersection

    return differs


def decks_expired(decks, expired=timedelta(days=1)):
    """
    检查 Decks 是否已过期
    :param decks: Decks 对象
    :param expired: 有效期长度
    :return: 若已过期则返回True
    """
    if os.path.isfile(decks.json_path):
        m_time = os.path.getmtime(decks.json_path)
        if datetime.fromtimestamp(m_time) < (datetime.today() - expired):
            return True
        else:
            return False
    return True


def cards_value(decks, mode=MODE_STANDARD):
    """
    区分职业的单卡价值排名，可在纠结是否合成或拆解时作为参考

    decks: 所在卡组数量
    games: 所在卡组游戏次数总和
    wins: 所在卡组获胜次数总和
    win_rate: 所在卡组平均胜率 (wins/games)
    *_rank: 在当前职业所有卡牌中的 * 排名
    *_rank%: 在当前职业所有卡牌中的 * 排名百分比 (排名/卡牌数)

    :param decks: 卡组合集，作为分析数据源
    :param mode: 模式
    :return: 单卡价值排名数据
    """

    if not isinstance(decks, Decks):
        raise TypeError('from_decks 须为 Decks 对象')

    total = 'total'
    ranked_keys = 'decks', 'games', 'wins', 'win_rate'
    rpf = '_rank'
    ppf = '%'

    stats = dict()
    stats[total] = dict()

    for deck in decks.search(mode=mode):
        career = deck.career
        if career not in stats:
            stats[career] = dict()
        for card, count in deck.cards.items():
            for k in total, career:
                if card not in stats[k]:
                    stats[k][card] = dict(
                        decks=0, games=0, wins=0, count=0)
                stats[k][card]['decks'] += 1
                stats[k][card]['games'] += deck.games or 0
                stats[k][card]['wins'] += deck.wins or 0
                stats[k][card]['count'] += count

    for k in stats:
        for c in stats[k]:
            try:
                stats[k][c]['win_rate'] = stats[k][c]['wins'] / stats[k][c]['games']
            except ZeroDivisionError:
                stats[k][c]['win_rate'] = None
            stats[k][c]['avg_count'] = stats[k][c]['count'] / stats[k][c]['decks']

    rkvl = dict()

    for k in stats:
        if k not in rkvl:
            rkvl[k] = dict()
        for rk in ranked_keys:
            vl = [s[rk] for c, s in stats[k].items()]
            vl = list(filter(lambda x: x, vl))
            vl.sort(reverse=True)
            rkvl[k][rk] = vl

    for k in stats:
        for c in stats[k]:
            for rk in ranked_keys:
                if stats[k][c][rk]:
                    rank = rkvl[k][rk].index(stats[k][c][rk]) + 1
                    stats[k][c][rk + rpf] = rank
                    stats[k][c][rk + rpf + ppf] = rank / len(stats[k])
                else:
                    stats[k][c][rk + rpf] = None
                    stats[k][c][rk + ppf] = None

    return stats


def get_all_decks(
        hsn_email=None, hsn_password=None,
        hsn_min_games=300, hsn_created_after=days_ago(30),
        expired=timedelta(days=1)
):
    """
    获得获取所有卡组数据
    :param hsn_email: Hearthstats 的登陆邮箱
    :param hsn_password: Hearthstats 的登陆密码
    :param hsn_min_games: Hearthstats 的搜索参数 最少游戏次数
    :param hsn_created_after: Hearthstats 最早更新时间
    :param expired: 过期时间，若载入的数据是次时间前获得的，则重新获取新数据
    :return: 返回 Decks 对象，包含所有数据源的卡组
    """

    decks = Decks()

    hsb = HSBoxDecks()
    if decks_expired(hsb, expired):
        hsb.update()
    decks.extend(hsb)

    if hsn_email and hsn_password:
        hsn = HearthStatsDecks()
        if decks_expired(hsn, expired):
            hsn.login(hsn_email, hsn_password)
            hsn.search_online(min_games=hsn_min_games, created_after=hsn_created_after)
        decks.extend(hsn)

    return decks


class DeckGenerator:
    def __init__(
            self,
            career, decks,
            include=None, exclude=None,
            mode=MODE_STANDARD):

        """
        通过若干包含游戏次数和胜率的卡组合集，找出其中高价值的卡牌，生成新的卡组(.cards)

        :param career: 指定职业
        :param decks: 来源卡组合集
        :param include: 生成的新卡组中将包含这些卡，应为 dict 对象，key为卡牌，value为数量
        :param exclude: 生成的新卡组中将排除这些卡，应为 dict 对象，key为卡牌，value为数量
        :param mode: 指定模式
        """

        self._career = None
        self.cards_stats = None
        self.top_decks = None

        self.career = career

        if decks and not isinstance(decks, list):
            raise TypeError('decks 应为 list')
        self.decks = decks or list()

        if include and not isinstance(include, dict):
            raise TypeError('include 应为 dict')
        self.include = include or Counter()

        if exclude and not isinstance(exclude, dict):
            raise TypeError('exclude 应为 dict')
        self.exclude = exclude or Counter()

        self.mode = mode

        self.top_decks_total_games = None
        self._gen_cards_stats()

    @property
    def cards(self):

        cards = Counter(self.include)

        exclude = Counter(self.exclude)

        for card, stats in self.cards_stats:
            count = 2 if stats['avg_count'] > 1.5 else 1

            if cards.get(card, 0) > count:
                count = 1 if card.rarity == 'LEGENDARY' else 2

            if card in exclude:
                count -= exclude.get(card)
                if count < 1:
                    logging.info('排除卡牌: {}'.format(card.name))
                    continue

            games_percentage = stats['total_games'] / self.top_decks_total_games
            if card not in self.include and games_percentage < 0.1:
                logging.info('排除冷门卡牌: {} (使用率 {:.2%})'.format(
                    card.name, games_percentage))
                continue

            cards[card] = count

            cards_count = sum(list(cards.values()))
            if cards_count == 30:
                break
            elif cards_count > 30:
                cards.subtract([card])
                break

        total_count = sum(cards.values())
        if total_count < 30:
            logging.warning('推荐卡牌数量不足，仅为 {} 张!'.format(total_count))

        return Counter(dict(filter(lambda x: x[1] > 0, cards.items())))

    @property
    def career(self):
        return self._career

    @career.setter
    # TODO: 考虑做成公共的
    def career(self, value):
        if not value:
            raise ValueError('career 不可为空')
        if isinstance(value, Career):
            career = value
        elif isinstance(value, str):
            career = CAREERS.search(value)
        else:
            raise TypeError('career 不支持 {} 类型的数值'.format(type(value).__name__))

        if career in (CAREERS.get('NEUTRAL'), CAREERS.get('DREAM')):
            raise ValueError('不能为该职业: {}'.format(career.name))

        if not career:
            raise ValueError('未找到该职业: {}'.format(value))

        self._career = career
        logging.info('设置职业为: {}'.format(career.name))

    def __setattr__(self, key, value):
        super(DeckGenerator, self).__setattr__(key, value)
        if key in ('career', 'decks', 'mode') and self.cards_stats:
            self._gen_cards_stats()

    def _gen_cards_stats(self):
        decks = list(filter(lambda x: x.games, self.decks))
        self.decks = Decks(decks)

        cards_stats, self.top_decks = self.decks.career_cards_stats(
            career=self.career, mode=self.mode, top_win_rate_percentage=0.1)

        self.top_decks_total_games = sum(map(lambda x: x.games, self.top_decks))

        self.cards_stats = list(cards_stats.items())
        self.cards_stats.sort(key=lambda x: x[1]['avg_win_rate'], reverse=True)

    def add_include(self, card, count=1):
        self.include.update({card: count})

    def add_exclude(self, card, count=1):
        self.exclude.update({card: count})

    def remove_include(self, card, count=1):
        self.include.subtract({card: count})

    def remove_exclude(self, card, count=1):
        self.exclude.subtract({card: count})


def print_cards(cards, return_text_only=False, sep=' ', rarity=True):
    """
    但法力值从小到大打印卡牌列表
    :param cards: 卡牌 list 或 Counter
    :param return_text_only: 选项，仅返回文本
    :param sep: 卡牌名称和数量之间的分隔符
    """

    if isinstance(cards, list):
        cards = Counter(cards)
    elif not isinstance(cards, Counter):
        raise TypeError('cards 参数应为 list 或 Counter 类型')

    cards = list(cards.items())
    cards.sort(key=lambda x: x[0].name)
    cards.sort(key=lambda x: x[0].cost or 0)

    text = list()
    for card, count in cards:
        line = '{}{}{}'.format(card.name, sep, count)
        if rarity and card.rarity not in ('FREE', 'COMMON'):
            line = '({}) {}'.format(card.rarity[0], line)
        text.append(line)
    text = '\n'.join(text)

    if return_text_only:
        return text
    else:
        print(text)


def cards_to_csv(save_path, cards=None):

    """
    将卡牌保存为 CSV 文件，方便使用 Excel 等工具进行分析
    :param cards: cards 对象
    :param save_path: 保存路径，例如 cards.csv
    """

    if cards is None:
        cards = Cards()

    # 仅列出相对常用的字段
    fields = [
        'id', 'name', 'text', 'cost', 'overload', 'type', 'race',
        'careers', 'multiClassGroup', 'set', 'collectible',
        'rarity', 'dust', 'howToEarn', 'howToEarnGolden',
        'health', 'attack', 'durability', 'spellDamage',
    ]

    with open(save_path, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for card in cards:
            row = list()
            for field in fields:
                field = getattr(card, field)
                if isinstance(field, (list, tuple, set)):
                    field = ', '.join(list(map(str, field)))
                elif isinstance(field, type(None)):
                    field = ''
                elif not isinstance(field, (str, int, float)):
                    field = str(field)
                row.append(field)
            writer.writerow(row)
