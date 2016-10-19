import unittest
import os

import hsdata


class Tests(unittest.TestCase):

    def setUp(self):
        if hsdata.core.MAIN_LANGUAGE != 'zhCN':
            hsdata.set_main_language('zhCN')

    def test_career(self):
        career = hsdata.Career('MAGE')
        self.assertEqual(career.name, '法师')
        self.assertEqual(career.__repr__(), '<Career: 法师 (MAGE)>')

        hsdata.set_main_language('enUS')
        career = hsdata.Career('MAGE')
        self.assertEqual(career.name, 'Mage')

    def test_careers(self):
        self.assertEqual(len(hsdata.CAREERS), 11)
        self.assertEqual(hsdata.CAREERS.get('HUNTER').name, '猎人')

        hsdata.Cards()
        self.assertEqual(hsdata.CAREERS.search('雷 萨').name, '猎人')
        self.assertEqual(hsdata.CAREERS.search('迪，麦 文').name, '法师')

        hsdata.set_main_language('enUS')
        hsdata.Cards()
        self.assertEqual(hsdata.CAREERS.search('Rexxar').name, 'Hunter')

    def test_card(self):
        card = hsdata.Cards().get('OG_134')
        self.assertEqual(card.name, '尤格-萨隆')
        self.assertEqual(card.career.name, '中立')

    def test_cards(self):
        cards = hsdata.Cards()
        found = cards.search('萨隆', '每 施放', return_first=False)
        self.assertEqual(len(found), 1)
        card = cards.get('OG_134')
        self.assertEqual(found[0], card)
        self.assertEqual(cards.search(in_text='每 召唤 随从 随机 敌方 伤害').name, '飞刀杂耍者')
        self.assertIsNone(cards.search('关门放狗', career='mage'))
        self.assertIsInstance(cards.search('海盗', return_first=False), list)

    def test_cards_update(self):
        test_json_path = 'p_cards_update_test.json'
        cards = hsdata.Cards(test_json_path)
        cards.update(hs_version_code=14366)
        os.remove(test_json_path)
        self.assertEqual(cards.search('兽群 呼唤', '三种').cost, 8)

    def test_deck(self):
        decks = hsdata.HSBoxDecks()
        deck = decks[10]
        self.assertIsInstance(deck.career, hsdata.Career)
        self.assertIsInstance(list(deck.cards.keys())[0], hsdata.Card)
        self.assertEqual(len(list(deck.cards.elements())), 30)

    def test_decks(self):
        decks1 = hsdata.HSBoxDecks()
        decks_count1 = len(decks1)
        os.remove(decks1.json_path)
        decks2 = hsdata.HSBoxDecks()
        decks_count2 = len(decks2)
        self.assertGreaterEqual(decks_count2, decks_count1)

        deck = decks1[100]
        self.assertIs(decks1.get(deck.id), deck)

        deck = decks2[1000]
        self.assertIs(decks2.get(deck.id), deck)

        found = decks2.search('萨满', hsdata.MODE_STANDARD, 0.5, 500, 5000, 5)
        self.assertLessEqual(len(found), 5)
        last_win_rate = 1
        for deck in found:
            self.assertEqual(deck.career, hsdata.CAREERS.get('SHAMAN'))
            self.assertEqual(deck.mode, hsdata.MODE_STANDARD)
            self.assertGreaterEqual(deck.win_rate, 0.5)
            self.assertGreaterEqual(deck.users, 500)
            self.assertGreaterEqual(deck.games, 5000)
            self.assertLessEqual(deck.win_rate, last_win_rate)
            last_win_rate = deck.win_rate

if __name__ == '__main__':
    unittest.main()
