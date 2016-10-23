#!/usr/bin/env python3
# coding: utf-8


"""
炉石盒子的卡组和卡组合集类
"""

import json
import logging
import re
from datetime import datetime

import requests
import scrapy
import scrapy.utils.log
from scrapy.crawler import CrawlerProcess

from .core import Deck, Decks, CAREERS, DATE_TIME_FORMAT

# 该来源的标识
SOURCE_NAME = 'HSBOX'

# 默认的载入和保存文件名，将与 DATA_DIR 拼接
JSON_FILE_NAME = 'Decks_{}.json'.format(SOURCE_NAME)

CAREER_MAP = {
    1: CAREERS.get('WARRIOR'),
    2: CAREERS.get('SHAMAN'),
    3: CAREERS.get('ROGUE'),
    4: CAREERS.get('PALADIN'),
    5: CAREERS.get('HUNTER'),
    6: CAREERS.get('DRUID'),
    7: CAREERS.get('WARLOCK'),
    8: CAREERS.get('MAGE'),
    9: CAREERS.get('PRIEST'),
}


class HSBoxDeck(Deck):
    # from: http://hs.gameyw.netease.com/box_groups.html
    # 该类卡组的 source 属性
    source = SOURCE_NAME
    DECK_URL_TEMPLATE = 'http://hs.gameyw.netease.com/box_group_details.html?code={}'

    def __init__(self):
        super(HSBoxDeck, self).__init__()
        self.ranked_games = None
        self.ranked_wins = None
        self.users = None
        self.created_at = None

    @property
    def ranked_win_rate(self):
        if self.ranked_games:
            return self.ranked_wins / self.ranked_games

    @property
    def ranked_losses(self):
        if self.ranked_games:
            return self.ranked_games - (self.ranked_wins or 0)

    def to_dict(self):
        dct = super(HSBoxDeck, self).to_dict()
        dct['created_at'] = self.created_at.strftime(DATE_TIME_FORMAT)
        return dct

    def from_dict(self, dct, cards=None):
        created_at = dct.pop('created_at')
        if created_at:
            self.created_at = datetime.strptime(created_at, DATE_TIME_FORMAT)
        super(HSBoxDeck, self).from_dict(dct, cards)


class HSBoxDecks(Decks):
    # 当从本地JSON载入卡组时，将把每个卡组转化为该类
    deck_class = HSBoxDeck

    def update(self, json_path=None):
        """
        从"炉石传说盒子"获取最新的卡组数据，并保存为JSON
        :param json_path: JSON的保存路径
        """

        if not json_path:
            json_path = self.json_path

        logging.info('开始更新炉石盒子卡组数据，将保存到 {}'.format(json_path))

        # 卡组的主要信息
        url_data = 'http://hs.gameyw.netease.com/json/pm20835.js'

        rp_json_in_js = re.compile(r'var\s+(\w+)\s*=\s*(.+);')
        session = requests.Session()

        def get_num(parent, key_name, to_float=False):
            num = parent.get(key_name)
            if num == '':
                num = None
            if num is not None:
                if to_float:
                    num = float(num)
                else:
                    num = int(num)
            return num

        def get_json(url):
            resp = session.get(url)
            resp.raise_for_status()
            m = rp_json_in_js.search(resp.text)
            return json.loads(m.group(2))

        decks_data = get_json(url_data)

        self.clear()

        for data in decks_data:
            deck = HSBoxDeck()

            deck.name = data.get('title')
            deck.id = data.get('md5key')

            if deck.id == 'fdc3c6fdde8b98ed1596cac5d1ad42e6':
                # 炉石盒子BUG，该卡组引用了一张不存在的卡牌ID
                continue

            deck.career = CAREER_MAP.get(get_num(data, 'job'))

            for card_count in data['deckString']['toPage'].split(','):
                card_id, count = card_count.split(':')
                card = self.cards.get(card_id)
                if not card:
                    raise ValueError('缺少卡牌: {}'.format(card_id))
                count = int(count)
                deck.cards[card] = count
            else:
                num_of_cards = sum(deck.cards.values())
                if num_of_cards != 30:
                    raise ValueError('{} 的卡牌数量为 {}，应为 30'.format(
                        deck, num_of_cards))

            deck.created_at = datetime.strptime(data.get('time'), '%Y-%m-%d %H:%M:%S')

            # 加入卡组合集
            self.append(deck)

        crawler_process = CrawlerProcess({'ITEM_PIPELINES': {'hsdata.hsbox.HSBoxScrapyPipeline': 1}})
        crawler_process.crawl(HSBoxScrapySpider, decks=self)
        crawler_process.start()

        # 保存卡组合集
        self.save(json_path)

        logging.info('炉石盒子卡组数据更新完成')


class HSBoxScrapyItem(scrapy.Item):
    games = scrapy.Field()
    wins = scrapy.Field()
    ranked_games = scrapy.Field()
    ranked_wins = scrapy.Field()
    users = scrapy.Field()
    deck_index = scrapy.Field()


class HSBoxScrapySpider(scrapy.Spider):
    name = 'hsbox_results'

    def __init__(self, decks):
        super(HSBoxScrapySpider, self).__init__()
        self.decks = decks

    def start_requests(self):
        request_list = list()

        for deck in self.decks:
            request_list.append(scrapy.http.Request(
                url=HSBoxDeck.DECK_URL_TEMPLATE.format(deck.id),
                meta=dict(deck_index=self.decks.index(deck))
            ))
        return request_list

    def parse(self, response):
        data = json.loads(response.text)
        if data['status']:
            item = HSBoxScrapyItem()
            r = data['data']

            item['games'] = r['offensive_count'] + r['subsequent_count']
            item['wins'] = r['offensive_win'] + r['subsequent_win']
            item['ranked_games'] = r['rank_count']
            item['ranked_wins'] = r['rank_win']
            item['users'] = r['users']

            item['deck_index'] = response.meta['deck_index']

            yield item


class HSBoxScrapyPipeline:
    @staticmethod
    def process_item(item, spider):
        deck = spider.decks[item['deck_index']]
        deck.games = item['games']
        deck.wins = item['wins']
        deck.ranked_games = item['ranked_games']
        deck.ranked_wins = item['ranked_wins']
        deck.users = item['users']
