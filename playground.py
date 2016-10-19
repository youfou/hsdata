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
