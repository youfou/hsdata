#!/usr/bin/env python3
# coding: utf-8


"""
一些实用的小功能
"""

import os
from collections import Counter
from datetime import datetime, timedelta

from .core import Deck, Decks, MODE_STANDARD


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
    :return: 新的卡组
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
