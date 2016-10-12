#! /bin/bash

# 更新卡牌、卡组，以及实战数据

python3 -c "from core import *; data=Data(); data.update(); print('Cards and decks updated! :D' + '\n' * 5)"

cd hs_deck_results
scrapy crawl results -a data_path=../data/data.json -a save_path=../data/results.json
