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

from .core import Deck, Decks, CAREERS, MODE_STANDARD, MODE_WILD

# 该来源的标识
SOURCE_NAME = 'HSBOX'

# 默认的载入和保存文件名，将与 DATA_DIR 拼接
JSON_FILE_NAME = 'Decks_{}.json'.format(SOURCE_NAME)


class HSBoxDeck(Deck):
    # from: http://hs.gameyw.netease.com/box_groups.html
    # 该类卡组的 source 属性
    source = SOURCE_NAME


class HSBoxDecks(Decks):
    # 当从本地JSON载入卡组时，将把每个卡组转化为该类
    deck_class = HSBoxDeck
    # 用于默认 json_path 文件名
    source = SOURCE_NAME

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

        careers_dict = {
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

            deck.career = careers_dict.get(get_num(data, 'job'))
            if data.get('game_mode') == '标准':
                deck.mode = MODE_STANDARD
            elif data.get('game_mode') == '狂野':
                deck.mode = MODE_WILD

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

            deck.updated_at = datetime.strptime(data.get('time'), '%Y-%m-%d %H:%M:%S')
            deck.url = data.get('jump_url').strip()

            # 加入卡组合集
            self.append(deck)
            # 加入卡组ID索引，用于 .get() 方法
            self._index[deck.id] = deck

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
    url_base = 'http://hs.gameyw.netease.com/hs/c/get-cg-info?&cgcode={}'

    def __init__(self, decks):
        super(HSBoxScrapySpider, self).__init__()
        self.decks = decks

    def start_requests(self):
        request_list = list()

        for deck in self.decks:
            request_list.append(scrapy.http.Request(
                url=self.url_base.format(deck.id),
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


class HSBoxScrapyPipeline(object):
    @staticmethod
    def process_item(item, spider):
        deck = spider.decks[item['deck_index']]
        deck.games = item['games']
        deck.wins = item['wins']
        deck.ranked_games = item['ranked_games']
        deck.ranked_wins = item['ranked_wins']
        deck.users = item['users']
