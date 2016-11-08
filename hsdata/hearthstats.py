#!/usr/bin/env python3
# coding: utf-8

"""
HearthStats 的卡组和卡组合集类
"""

import json
import logging
import multiprocessing
import re
from collections import Counter
from datetime import datetime
from urllib.parse import urlencode

import requests
import scrapy
from scrapy.crawler import CrawlerProcess

from .core import (
    DATE_TIME_FORMAT,
    Deck, Decks, CAREERS, CARDS,
    get_career, days_ago
)

# 该来源的标识
SOURCE_NAME = 'HEARTHSTATS'

# 默认的载入和保存文件名，将与 DATA_DIR 拼接
JSON_FILE_NAME = 'Decks_{}.json'.format(SOURCE_NAME)

ORDER_BY_DESC = 'desc'
ORDER_BY_ASC = 'asc'

SORT_BY_CREATED_AT = 'created_at'
SORT_BY_LOSSES = 'num_losses'
SORT_BY_GAMES = 'num_matches'
SORT_BY_MINIONS = 'num_minions'
SORT_BY_NAME = 'name'
SORT_BY_SPELLS = 'num_spells'
SORT_BY_USERS = 'num_users'
SORT_BY_WEAPONS = 'num_weapons'
SORT_BY_WIN_RATE = 'winrate'
SORT_BY_WINS = 'num_wins'

CAREER_MAP = {
    'DRUID': 1,
    'HUNTER': 2,
    'MAGE': 3,
    'PALADIN': 4,
    'PRIEST': 5,
    'ROGUE': 6,
    'SHAMAN': 7,
    'WARLOCK': 8,
    'WARRIOR': 9,
}


class HearthStatsDeck(Deck):
    # from: http://hearthstats.net/decks/search
    # 该类卡组的 source 属性
    source = SOURCE_NAME
    DECK_URL_TEMPLATE = 'http://hearthstats.net/decks/{}/public_show'

    def __init__(self):
        super(HearthStatsDeck, self).__init__()
        self.creator_id = None
        self.win_rate_by_rank = dict()

    def from_dict(self, dct, cards=None):
        win_rate_by_rank = dct.pop('win_rate_by_rank')
        for rank, win_rate in win_rate_by_rank.items():
            self.win_rate_by_rank[int(rank)] = win_rate
        super(HearthStatsDeck, self).from_dict(dct, cards)


class HearthStatsDecks(Decks):
    # 当从本地JSON载入卡组时，将把每个卡组转化为该类
    deck_class = HearthStatsDeck

    def __init__(self, email=None, password=None, json_path=None, auto_load=True):
        """
        使用 HearthStats 数据源，必须先注册其网站账号后，并在登录后使用
        该数据源没有无需使用 update 方法，请通过 search_online 方法获取卡组数据
        注册页面: http://hearthstats.net/users/sign_up
        :param email: 登录邮箱
        :param password: 登录密码
        """
        logging.info('初始化卡组合集 (HearthStats)')
        super(HearthStatsDecks, self).__init__(
            json_path=json_path,
            auto_load=auto_load,
            update_if_not_found=False)

        self.session = requests.Session()
        self._logged_in = False
        self.search_url = None

        self.login(email, password)

    @property
    def logged_in(self):
        return self._logged_in

    def update(self, json_path=None):
        logging.warning('该数据来源不支持 update 方法，请直接使用 search_online 方法')

    def login(self, email, password):
        if not email or not password:
            self._logged_in = False
            return
        logging.info('正在登录 HearthStats')
        r = self.session.post(
            url='http://hearthstats.net/api/v3/users/sign_in',
            json=dict(user_login=dict(email=email, password=password))
        )
        r.raise_for_status()
        if r.json().get('success'):
            self._logged_in = True
            logging.info('登录成功')
        else:
            raise Exception('登陆失败: {}'.format(r.json().get('message')))

    def search_online(
            self,
            career=None,
            created_after=days_ago(30),
            min_games=300,
            name='',
            sort_by=SORT_BY_WIN_RATE,
            order_by=ORDER_BY_DESC,
    ):
        """
        在 hearthstats 网站中搜索卡组
        :param career: 职业
        :param created_after: 在 XXXX-XX-XX 后创建
        :param min_games: 最少游戏次数
        :param name: 卡组名称
        :param sort_by: 排列方式
        :param order_by: 正序或倒序
        """

        if not self._logged_in:
            logging.warning('尚未登录账号')
            return

        if not career:
            career = ''
        else:
            career = get_career(career)
            career = CAREER_MAP[career.class_name]

        if not created_after:
            created_after = ''
        elif isinstance(created_after, datetime):
            created_after = created_after.strftime(DATE_TIME_FORMAT)

        qs = urlencode({
            'utf8': '✓',
            'q[klass_id_eq]': career,
            'q[unique_deck_created_at_gteq]': created_after,
            'q[unique_deck_num_matches_gteq]': min_games,
            'q[name_cont]': name,
            'items': 1000000,
            'sort': sort_by,
            'order': order_by,
            'commit': 'Apply',
        })

        self.search_url = 'http://hearthstats.net/decks/search?{}'.format(qs)

        logging.info('正在搜索卡组')

        r = self.session.get(self.search_url)
        r.raise_for_status()

        deck_ids = re.findall(r'(?<=href="/decks/)[^/]+(?=/public_show)', r.text)

        if not deck_ids:
            logging.info('未找到符合条件的卡组，试试放宽条件吧')
            return

        logging.info('找到 {} 个符合条件的卡组'.format(len(deck_ids)))

        # 清除原有的数据
        self.clear()

        # 使用单独进程来运行爬虫，绕过 twisted reactor 无法重用的问题
        with multiprocessing.Pool() as p:
            decks = p.apply(self._crawl, (deck_ids,))

        if decks:
            # 爬完后的内容是乱序的，需恢复为原结果列表的顺序
            decks.sort(key=lambda x: deck_ids.index(x.id))
            # 加入到卡组合集中
            self.extend(decks)

        logging.info('卡组数据获取完成 ({}/{})'.format(
            len(self), len(deck_ids)
        ))

        self.save()

    @staticmethod
    def _crawl(deck_ids):
        logging.info('正在获取卡组数据')
        decks = list()
        cp = CrawlerProcess({'ITEM_PIPELINES': {'hsdata.hearthstats.HearthStatsScrapyPipeline': 1}})
        cp.crawl(HearthStatsScrapySpider, deck_ids=deck_ids, decks=decks)
        cp.start()
        return decks


class HearthStatsScrapyItem(scrapy.Item):
    name = scrapy.Field()
    id = scrapy.Field()
    career = scrapy.Field()
    cards = scrapy.Field()
    games = scrapy.Field()
    wins = scrapy.Field()
    draws = scrapy.Field()
    creator_id = scrapy.Field()
    win_rate_by_rank = scrapy.Field()


class HearthStatsScrapySpider(scrapy.Spider):
    name = 'hearthstats_decks'

    def __init__(self, deck_ids, decks):
        super(HearthStatsScrapySpider, self).__init__()
        self.deck_ids = deck_ids
        self.decks = decks

    def start_requests(self):
        request_list = list()

        for deck_id in self.deck_ids:
            request_list.append(scrapy.http.Request(
                url=HearthStatsDeck.DECK_URL_TEMPLATE.format(deck_id),
                meta=dict(deck_id=deck_id)
            ))
        return request_list

    def parse(self, response):

        item = HearthStatsScrapyItem()

        item['name'] = response.xpath('//meta[@name="description"]/@content').extract()[0]
        item['id'] = response.meta['deck_id']

        block_1 = response.css('div.col-md-4.col-sm-4.col-xs-4 div.win-count')

        item['creator_id'] = block_1[0].xpath('.//a/@href').extract()[0].rsplit('/', 1)[1]
        item['career'] = CAREERS.get(block_1[1].xpath('.//img/@alt').extract()[0].upper())

        block_2 = response.css('div.col-md-2.col-sm-2.col-xs-4 div.win-count span')
        item['wins'] = int(block_2[0].xpath('text()')[0].extract())
        losses = int(block_2[1].xpath('text()')[0].extract())
        item['draws'] = int(block_2[2].xpath('text()')[0].extract())
        item['games'] = item['wins'] + losses + item['draws']

        cards = Counter()

        for card_div in response.css('div.card.cardWrapper'):
            img_src = card_div.xpath('img[@class="image"]/@src').extract()[0]
            card_id = img_src.rsplit('/', 1)[1].split('.', 1)[0]
            card = CARDS.get(card_id)
            count = int(card_div.xpath('div[@class="qty"]/text()')[0].extract())
            cards[card] = count

        item['cards'] = cards

        try:
            m = re.search(r'(?<=gon\.rank_wr=)[\[\],.\d\s]+?(?=;)', response.text)
            win_rate_by_rank = dict(json.loads(m.group()))
            if win_rate_by_rank:
                for rank in win_rate_by_rank:
                    win_rate_by_rank[rank] /= 100
            item['win_rate_by_rank'] = win_rate_by_rank
        except (ValueError, TypeError, json.JSONDecodeError):
            item['win_rate_by_rank'] = dict()

        yield item


class HearthStatsScrapyPipeline:
    @staticmethod
    def process_item(item, spider):
        deck = HearthStatsDeck()

        deck.name = item['name']
        deck.id = item['id']
        deck.career = item['career']
        deck.cards = item['cards']
        deck.games = item['games']
        deck.wins = item['wins']
        deck.draws = item['draws']
        deck.creator_id = item['creator_id']
        deck.win_rate_by_rank = item['win_rate_by_rank']

        spider.decks.append(deck)
