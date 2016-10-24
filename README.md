# hsdata

**用数据玩炉石**

快速收集和分析炉石传说的卡牌及卡组数据

## 运行环境

hsdata 使用 Python 3 编写，引用了 requests 和 scrapy 两个模块，理论上可以在所有支持这两个模块的系统环境中运行。

## 如何安装

推荐使用 pip 安装

    pip3 install -U hsdata

## 快速上手

```python

import hsdata

# 获取卡组数据
decks = hsdata.HSBoxDecks()
# 若未找到本地数据，会自动从网络获取
print('从炉石盒子获取到', len(decks), '个卡组数据！')

# 更新卡组数据
# decks.update()

# 搜索卡组
found = decks.search(
    career='萨满',
    mode=hsdata.MODE_STANDARD,
    min_games=10000,
    win_rate_top_n=5)
print('其中5个胜率最高的萨满卡组:')
for deck in found:
    print('{}: {} 场, {:.2%} 胜'.format(
        deck.name, deck.games, deck.win_rate))

# 查看卡组中的卡牌
print('其中第一个卡组用了这些卡牌')
print(found[0].cards)

```

运行结果类似这样

> 从炉石盒子获取到 1574 个卡组数据！  
>   
> 其中5个胜率最高的萨满卡组:  
> 【黄金赛冠军】OmegaZero中速萨: 124830 场, 63.47% 胜  
> 【欧服登顶】Janos 中速萨: 172444 场, 63.02% 胜  
> 【EULC冠军】Pavel中速萨: 61187 场, 62.73% 胜  
> 【欧服前50】Toymachine中速萨: 41754 场, 60.95% 胜  
> 【外服登顶】Ownerism 中速萨: 152966 场, 60.94% 胜  
>   
> 其中第一个卡组用了这些卡牌  
> Counter({\<Card: 坑道穴居人 (LOE_018)>: 2,  
> \<Card: 大漩涡传送门 (KAR_073)>: 2,  
> \<Card: 碧蓝幼龙 (EX1_284)>: 2,  
> \<Card: 幽灵之爪 (KAR_063)>: 2,  
> \<Card: 火元素 (CS2_042)>: 2,  
> \<Card: 巴内斯 (KAR_114)>: 1,  
> \<Card: 银色侍从 (EX1_008)>: 1,  
> \<Card: 血法师萨尔诺斯 (EX1_012)>: 1,  
> \<Card: 野性狼魂 (EX1_248)>: 2,  
> \<Card: 法力之潮图腾 (EX1_575)>: 2,  
> \<Card: 深渊魔物 (OG_028)>: 2,  
> \<Card: 闪电箭 (EX1_238)>: 2,  
> \<Card: 雷霆崖勇士 (AT_049)>: 2,  
> \<Card: 火舌图腾 (EX1_565)>: 2,  
> \<Card: 图腾魔像 (AT_052)>: 2,  
> \<Card: 闪电风暴 (EX1_259)>: 1,  
> \<Card: 妖术 (EX1_246)>: 2})  

以上只是个帮助入门的例子，发挥想象力，用它来探索更多吧！

## 数据来源

目前 hsdata 采用了以下数据来源，这些数据的版权为各数据源所有。

* 卡牌数据
    * [HearthstoneJSON](https://hearthstonejson.com/)
* 卡组数据
    * [网易炉石盒子](http://lushi.163.com/)
    * [HearthStats](http://hearthstats.net/)

----

许可协议: Apache License, Version 2.0
