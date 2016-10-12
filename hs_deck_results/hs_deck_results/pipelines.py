# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


import json


class HsDeckResultsPipeline(object):

    def __init__(self):
        self.results = {}

    def process_item(self, item, spider):
        key = item['result'].pop('cgcode')
        self.results[key] = item['result']

    def close_spider(self, spider):
        with open(spider.save_path, 'w') as fp:
            json.dump(self.results, fp)
