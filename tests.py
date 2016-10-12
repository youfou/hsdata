#!/usr/bin/env python3
# coding: utf-8


import unittest

from core import *


class Tests(unittest.TestCase):
    def setUp(self):
        self.data = Data()
        self.data.load()

    def test_career_converter(self):
        self.assertEqual(career_converter('猎人', to='id'), 5)
        self.assertEqual(career_converter('猎', to='id'), 5)
        self.assertEqual(career_converter('牧师', to='id'), 9)
        self.assertEqual(career_converter('牧', to='id'), 9)
        self.assertEqual(career_converter(3, to='name'), '潜行者')
        self.assertEqual(career_converter(7, to='name'), '术士')

    def test_cards_converter(self):
        with self.assertRaises(Exception):
            card_converter('尤格-萨隆')
        self.assertEqual(card_converter('OG_134', to='name'), '尤格-萨隆')
        card_obj = card_converter('OG_134', to='obj', data=self.data)
        self.assertIsInstance(card_obj, Card)
        self.assertEqual(card_obj.name, '尤格-萨隆')
        self.assertEqual(card_converter('奥金斧', to='id'), 'CS2_112')

    def test_get_jsons(self):
        self.assertGreater(len(self.data.jsons.get('HSCARDS')), 2000)
        self.assertGreater(len(self.data.jsons.get('pm20835')), 1000)
        self.assertGreater(len(self.data.jsons.get('pm19022')), 1000)

    def test_update_cards(self):
        new_data = Data()
        new_data._update_cards()
        self.assertEqual(len(new_data.cards), len(new_data.jsons.get('HSCARDS')))

        card_dict = new_data.cards['BRM_017'].to_dict()
        del card_dict['arena_played']
        del card_dict['arena_won']
        del card_dict['arena_picked']
        self.assertEqual(
            card_dict,
            dict(
                career_id=9, cost=2, card_set=14,
                description='随机召唤一个在本局对战中死亡的友方随从。',
                card_id='BRM_017', name='复活术', rarity=3,
                recommend='只要不是一费随从，就赚到了', score=7,
            )
        )

    def test_update_decks(self):
        new_data = Data()
        new_data._update_decks()
        self.assertEqual(len(new_data.decks), len(new_data.jsons.get('pm20835')))

    def test_save_and_load_data(self):
        self.data.save()
        loaded = Data()
        loaded.load()

        self.assertEqual(len(self.data.cards.items()), len(loaded.cards.items()))
        self.assertEqual(len(self.data.decks), len(loaded.decks))

        for card_id, loaded_card in loaded.cards.items():
            self.assertEqual(loaded_card.to_dict(), self.data.cards[card_id].to_dict())

        deck_index = 0
        for loaded_deck in loaded.decks:
            self.assertEqual(loaded_deck.to_dict(), self.data.decks[deck_index].to_dict())
            deck_index += 1

    def test_search_decks(self):
        decks = self.data.search_decks(
            career_id=career_name_to_id('萨满'),
            mode='标准',
            min_win_rate=0.60,
            min_users=1000
        )
        self.assertGreaterEqual(len(decks), 3)
        self.assertLessEqual(len(decks), 20)

    def test_search_card(self):

        card = self.data.search_card('放狗 关门')
        self.assertIn('关门', card.name)
        self.assertIn('放狗', card.name)

        cards = self.data.search_card('猎人', return_first=False)
        self.assertGreaterEqual(len(cards), 4)
        for card in cards:
            self.assertIn('猎人', card.name)

    def test_unities(self):
        from unities.common import career_cards_stats
        ret = career_cards_stats(1, return_top_decks_only=True, data=self.data)
        self.assertIsInstance(ret, list)
        self.assertIsInstance(ret[2], Deck)


if __name__ == '__main__':
    unittest.main()
