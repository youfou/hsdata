# -*- coding: utf-8 -*-

"""
:copyright: (c) 2016 by Youfou.
:license: Apache 2.0, see LICENSE for more details.
"""

import scrapy
import json

from hs_deck_results.items import HsDeckResultsItem


class ResultsSpider(scrapy.Spider):
    name = "results"

    def __init__(self, data_path=None, save_path=None):

        self.save_path = save_path

        with open(data_path, 'r') as fp:
            data = json.load(fp)

        self.start_urls = []

        for deck in data['decks']:
            self.start_urls.append(
                'http://hs.gameyw.netease.com'
                '/hs/c/get-cg-info?&cgcode={}'.format(deck['key']))

    def parse(self, response):
        result = json.loads(response.text)
        if result['status']:
            item = HsDeckResultsItem()
            item['result'] = result['data']
            yield item
