# hs_data

**炉石传说数据分析工具**

快速收集和分析炉石传说的卡牌及玩家卡组数据

> 当前数据来源为网易炉石盒子


## 快速上手

    from core import *

    # 创建数据对象
    data = Data()
    # 更新数据，或使用 .load() 载入上次更新的数据
    # data.update()
    data.load()

    # 搜索卡牌
    found = data.search_card('萨隆', return_first=False)
    print('找到卡牌:')
    print(found, '\n')

    # 按条件搜索卡组
    decks = data.search_decks(
        career_id=career_converter('萨满', 'id'),
        mode='标准',
        min_win_rate=0.6,
    )
    print('找到卡组:')
    print(decks, '\n')

    # 查看卡组信息
    deck = decks[0]
    print(deck, '卡组信息:')
    print('用户数:', deck.users)
    print('使用次数:', deck.played)
    print('胜率:', '{:.2%}'.format(deck.win_rate))
    print('卡牌:', [(data.card(k).name, v) for k, v in deck.cards.items()])

    # 更多玩法请见 playground.py

----

许可协议: Apache License, Version 2.0
