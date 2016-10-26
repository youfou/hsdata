#!/usr/bin/env python3
# coding: utf-8


"""
一些实用的小功能
"""

import os
from collections import Counter
from datetime import datetime, timedelta

from .core import (
    MODE_STANDARD,
    Deck, Decks,
    days_ago
)
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

    differs = dict()
    for deck in decks:
        differs[deck] = deck.cards - intersection

    return differs


def gen_deck(career, from_decks, mode=MODE_STANDARD):
    """
    根据给定的卡组合集生成指定职业和模式的新卡组
    :param career: 职业
    :param from_decks: 卡组合集
    :param mode: 模式
    :return: 新的卡组, 和参考用的卡组列表
    """

    if not isinstance(from_decks, Decks):
        raise TypeError('应为 Decks 对象')

    cards_stats, top_decks = from_decks.career_cards_stats(career, mode=mode)

    cards = Counter()
    for card, stats in cards_stats.items():
        count = 2 if stats['avg_count'] >= 1.75 else 1
        cards[card] = count
        if sum(cards.values()) == 30:
            break
        elif sum(cards.values()) > 30:
            cards.subtract([card])
            break

    new_deck = Deck()
    new_deck.cards = cards
    return new_deck, top_decks


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


def cards_value(from_decks, mode=MODE_STANDARD):
    """
    区分职业的单卡价值排名，可在纠结是否合成或拆解时作为参考

    decks: 所在卡组数量
    games: 所在卡组游戏次数总和
    wins: 所在卡组获胜次数总和
    win_rate: 所在卡组平均胜率 (wins/games)
    *_rank: 在当前职业所有卡牌中的 * 排名
    *_rank%: 在当前职业所有卡牌中的 * 排名百分比 (排名/卡牌数)

    :param from_decks: 卡组合集，作为分析数据源
    :param mode: 模式
    :return: 单卡价值排名数据
    """

    if not isinstance(from_decks, Decks):
        raise TypeError('from_decks 须为 Decks 对象')

    total = 'total'
    ranked_keys = 'decks', 'games', 'wins', 'win_rate'
    rpf = '_rank'
    ppf = '%'

    stats = dict()
    stats[total] = dict()

    for deck in from_decks.search(mode=mode):
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
        hsn_email, hsn_password,
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
    hsb = HSBoxDecks()
    if decks_expired(hsb, expired):
        hsb.update()

    hsn = HearthStatsDecks()
    if decks_expired(hsn, expired):
        hsn.login(hsn_email, hsn_password)
        hsn.search_online(min_games=hsn_min_games, created_after=hsn_created_after)

    decks = Decks()

    decks.extend(hsb)
    decks.extend(hsn)

    return decks
