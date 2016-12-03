import logging
import os
import unittest

import hsdata

logging.getLogger('scrapy').propagate = True
logging.getLogger('requests').propagate = True


class Tests(unittest.TestCase):
    def setUp(self):
        if hsdata.core.MAIN_LANGUAGE != 'zhCN':
            hsdata.set_main_language('zhCN')

    @staticmethod
    def remove_if_exists(path):
        if os.path.exists(path):
            os.remove(path)

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
        card = cards.get(found[0].id)
        self.assertEqual(found[0], card)
        self.assertEqual(cards.search(in_text='在你召唤一个随从后 随机 敌方 伤害').name, '飞刀杂耍者')
        self.assertIsNone(cards.search('关门放狗', career='mage'))
        self.assertIsInstance(cards.search('海盗', return_first=False), list)

    def test_cards_update(self):
        test_path = 'p_cards_update_test.json'

        self.remove_if_exists(test_path)

        try:
            cards = hsdata.Cards(test_path)
            cards.update(hs_version_code=14366)
        finally:
            self.remove_if_exists(test_path)

        self.assertEqual(cards.search('兽群 呼唤', '三种').cost, 8)

    def test_deck(self):
        decks = hsdata.HSBoxDecks()
        deck = decks[10]
        self.assertIsInstance(deck.career, hsdata.Career)
        self.assertIsInstance(list(deck.cards.keys())[0], hsdata.Card)
        self.assertEqual(len(list(deck.cards.elements())), 30)

    def test_hsbox_decks(self):

        test_path = 'p_hsbox_decks_test.json'
        self.remove_if_exists(test_path)

        try:
            updated_decks = hsdata.HSBoxDecks(json_path=test_path)
            updated_deck = updated_decks[100]
            loaded_decks = hsdata.HSBoxDecks(json_path=test_path)
            loaded_deck = loaded_decks.get(updated_deck.id)
        finally:
            self.remove_if_exists(test_path)

        self.assertEqual(len(updated_decks), len(loaded_decks))
        self.assertEqual(updated_deck.cards, loaded_deck.cards)

        self.assertIsNotNone(loaded_decks.source)
        self.assertIsNotNone(loaded_deck.source)

        self.assertTrue(
            updated_decks.source ==
            updated_deck.source ==
            loaded_decks.source ==
            loaded_deck.source
        )

        self.assertIs(loaded_decks.get(loaded_deck.id), loaded_deck)

        found = loaded_decks.search('萨满', hsdata.MODE_STANDARD, 0.5, 10000, 5)
        self.assertLessEqual(len(found), 5)
        last_win_rate = 1
        for deck in found:
            self.assertEqual(deck.career, hsdata.CAREERS.get('SHAMAN'))
            self.assertEqual(deck.mode, hsdata.MODE_STANDARD)
            self.assertGreaterEqual(deck.win_rate, 0.5)
            self.assertGreaterEqual(deck.games, 10000)
            self.assertLessEqual(deck.win_rate, last_win_rate)
            last_win_rate = deck.win_rate


if __name__ == '__main__':
    unittest.main()
