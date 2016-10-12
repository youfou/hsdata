#!/usr/bin/env python3
# coding: utf-8

"""
这是其中的一个玩法
~~~~~~~~~~~~~~~~
"""

from .common import Data, CAREERS, career_cards_stats


def do():
    """
    通过分析各职业的卡组，找出其中的优质卡牌，并加以分析，最终以 xlsx 格式保存到 cards_stats 目录
    """

    data = Data()
    data.load()

    for career_id in CAREERS:
        career_cards_stats(career_id, data=data)

