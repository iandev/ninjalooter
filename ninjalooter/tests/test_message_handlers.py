from unittest import mock

from ninjalooter import config
from ninjalooter import message_handlers
from ninjalooter import models
from ninjalooter.tests import base
from ninjalooter import utils


class TestMessageHandlers(base.NLTestBase):
    def setUp(self) -> None:
        utils.setup_aho()

    @mock.patch('wx.PostEvent')
    def test_handle_start_who(self, mock_post_event):
        # Empty List, full /who
        config.PLAYER_AFFILIATIONS = {}
        for line in base.SAMPLE_WHO_LOG.splitlines():
            match = config.MATCH_WHO.match(line)
            if match:
                message_handlers.handle_who(match, 'window')
        self.assertEqual(24, len(config.PLAYER_AFFILIATIONS))
        self.assertEqual(24, mock_post_event.call_count)
        mock_post_event.reset_mock()

        # Peter and Fred should be marked as guildless
        self.assertIsNone(config.PLAYER_AFFILIATIONS['Peter'])
        self.assertIsNone(config.PLAYER_AFFILIATIONS['Fred'])

        # Mark Peter and Fred as historically belonging to Kingdom
        config.HISTORICAL_AFFILIATIONS['Peter'] = 'Kingdom'
        config.HISTORICAL_AFFILIATIONS['Fred'] = 'Kingdom'

        # Trigger New Who
        message_handlers.handle_start_who(None, 'window')
        mock_post_event.assert_called_once_with(
            'window', models.ClearWhoEvent())
        mock_post_event.reset_mock()

        # Run the full who-list again
        for line in base.SAMPLE_WHO_LOG.splitlines():
            match = config.MATCH_WHO.match(line)
            if match:
                message_handlers.handle_who(match, 'window')
        self.assertEqual(24, len(config.PLAYER_AFFILIATIONS))

        # Peter should be marked as Kingdom, and Fred as guildless
        self.assertEqual('Kingdom', config.PLAYER_AFFILIATIONS['Peter'])
        self.assertIsNone(config.PLAYER_AFFILIATIONS['Fred'])

    @mock.patch('wx.PostEvent')
    def test_handle_who(self, mock_post_event):
        # Empty List, full /who
        config.PLAYER_AFFILIATIONS = {}
        for line in base.SAMPLE_WHO_LOG.splitlines():
            match = config.MATCH_WHO.match(line)
            if match:
                message_handlers.handle_who(match, 'window')
        self.assertEqual(24, len(config.PLAYER_AFFILIATIONS))
        self.assertEqual(24, mock_post_event.call_count)
        mock_post_event.reset_mock()

        # Member changed from ANONYMOUS/Unguilded to Guilded
        config.PLAYER_AFFILIATIONS = {'Jim': None}
        line = '[Sun Aug 16 22:46:32 2020] [ANONYMOUS] Jim (Gnome) <Guild>'
        match = config.MATCH_WHO.match(line)
        message_handlers.handle_who(match, 'window')
        self.assertEqual(1, len(config.PLAYER_AFFILIATIONS))
        self.assertEqual('Guild', config.PLAYER_AFFILIATIONS['Jim'])
        mock_post_event.assert_called_once_with(
            'window', models.WhoEvent('Jim', 'ANONYMOUS', '??', 'Guild'))
        mock_post_event.reset_mock()

        # Member changed guilds
        config.PLAYER_AFFILIATIONS = {'Jim': 'Guild'}
        line = '[Sun Aug 16 22:46:32 2020] [ANONYMOUS] Jim (Gnome) <Other>'
        match = config.MATCH_WHO.match(line)
        message_handlers.handle_who(match, 'window')
        self.assertEqual(1, len(config.PLAYER_AFFILIATIONS))
        self.assertEqual('Other', config.PLAYER_AFFILIATIONS['Jim'])
        mock_post_event.assert_called_once_with(
            'window', models.WhoEvent('Jim', 'ANONYMOUS', '??', 'Other'))
        mock_post_event.reset_mock()

        # Member left their guild
        config.PLAYER_AFFILIATIONS = {'Jim': 'Guild'}
        line = '[Sun Aug 16 22:46:32 2020] [50 Cleric] Jim (Gnome)'
        match = config.MATCH_WHO.match(line)
        message_handlers.handle_who(match, 'window')
        self.assertEqual(1, len(config.PLAYER_AFFILIATIONS))
        self.assertIsNone(config.PLAYER_AFFILIATIONS['Jim'])
        mock_post_event.assert_called_once_with(
            'window', models.WhoEvent('Jim', 'Cleric', '50', None))
        mock_post_event.reset_mock()

        # Some bad line is passed somehow
        config.PLAYER_AFFILIATIONS = {}
        line = "???"
        match = config.MATCH_WHO.match(line)
        message_handlers.handle_who(match, 'window')
        self.assertEqual(0, len(config.PLAYER_AFFILIATIONS))
        mock_post_event.assert_not_called()

    @mock.patch('wx.PostEvent')
    def test_handle_ooc(self, mock_post_event):
        config.PLAYER_AFFILIATIONS = {
            'Jim': 'Venerate',
            'James': 'Kingdom',
            'Dan': 'Dial a Daniel',
        }
        config.PENDING_AUCTIONS = list()
        # Item linked by a non-federation guild member
        line = ("[Sun Aug 16 22:47:31 2020] Dan says out of character, "
                "'Copper Disc'")
        match = config.MATCH_OOC.match(line)
        items = message_handlers.handle_ooc(match, 'window')
        self.assertEqual(0, len(items))
        self.assertEqual(0, len(config.PENDING_AUCTIONS))
        mock_post_event.assert_not_called()

        # Item linked by a federation guild member
        line = ("[Sun Aug 16 22:47:31 2020] Jim says out of character, "
                "'Copper Disc'")
        jim_disc_1 = models.ItemDrop(
            'Copper Disc', 'Jim', 'Sun Aug 16 22:47:31 2020')
        match = config.MATCH_OOC.match(line)
        items = list(message_handlers.handle_ooc(match, 'window'))
        self.assertEqual(1, len(items))
        self.assertIn('Copper Disc', items)
        self.assertEqual(1, len(config.PENDING_AUCTIONS))
        self.assertListEqual(
            [jim_disc_1],
            config.PENDING_AUCTIONS)
        mock_post_event.assert_called_once_with(
            'window', models.DropEvent())
        mock_post_event.reset_mock()

        # Two items linked by a federation guild member, plus chat
        line = ("[Sun Aug 16 22:47:41 2020] James says out of character, "
                "'Copper Disc and Platinum Disc woot'")
        james_disc_1 = models.ItemDrop(
            'Copper Disc', 'James', 'Sun Aug 16 22:47:41 2020')
        james_disc_2 = models.ItemDrop(
            'Platinum Disc', 'James', 'Sun Aug 16 22:47:41 2020')
        match = config.MATCH_OOC.match(line)
        items = list(message_handlers.handle_ooc(match, 'window'))
        self.assertEqual(2, len(items))
        self.assertIn('Copper Disc', items)
        self.assertIn('Platinum Disc', items)
        self.assertListEqual(
            [jim_disc_1, james_disc_1, james_disc_2],
            config.PENDING_AUCTIONS)
        mock_post_event.assert_called_once_with(
            'window', models.DropEvent())
        mock_post_event.reset_mock()

        # Random chatter by federation guild member
        line = ("[Sun Aug 16 22:47:31 2020] Jim says out of character, "
                "'four score and seven years ago, we wanted pixels'")
        match = config.MATCH_OOC.match(line)
        items = list(message_handlers.handle_ooc(match, 'window'))
        self.assertEqual(0, len(items))
        self.assertListEqual(
            [jim_disc_1, james_disc_1, james_disc_2],
            config.PENDING_AUCTIONS)
        mock_post_event.assert_not_called()

        # Some bad line is passed somehow
        line = "???"
        match = config.MATCH_OOC.match(line)
        items = list(message_handlers.handle_ooc(match, 'window'))
        self.assertEqual(0, len(items))
        self.assertListEqual(
            [jim_disc_1, james_disc_1, james_disc_2],
            config.PENDING_AUCTIONS)
        mock_post_event.assert_not_called()

    @mock.patch('wx.PostEvent')
    def test_handle_auc(self, mock_post_event):
        config.PLAYER_AFFILIATIONS = {
            'Jim': 'Venerate',
            'Tim': 'Kingdom',
            'Dan': 'Dial a Daniel',
        }
        item_name = 'Copper Disc'
        itemdrop = models.ItemDrop(item_name, "Jim", "timestamp")
        disc_auction = models.DKPAuction(itemdrop, 'VCR')
        config.ACTIVE_AUCTIONS = {
            item_name: disc_auction
        }

        # Someone in the alliance bids on an inactive item
        line = ("[Sun Aug 16 22:47:31 2020] Jim auctions, "
                "'Platinum Disc 10 DKP'")
        match = config.MATCH_AUC.match(line)
        result = message_handlers.handle_auc(match, 'window')
        self.assertFalse(result)
        self.assertEqual(None, disc_auction.highest())
        self.assertEqual(1, len(config.ACTIVE_AUCTIONS))
        mock_post_event.assert_not_called()

        # Someone outside the alliance bids on an active item
        line = ("[Sun Aug 16 22:47:31 2020] Dan auctions, "
                "'Copper Disc 10 DKP'")
        match = config.MATCH_AUC.match(line)
        result = message_handlers.handle_auc(match, 'window')
        self.assertFalse(result)
        self.assertIsNone(disc_auction.highest())
        mock_post_event.assert_not_called()

        # Someone we haven't seen bids on an active item
        line = ("[Sun Aug 16 22:47:31 2020] Paul auctions, "
                "'Copper Disc 10 DKP'")
        match = config.MATCH_AUC.match(line)
        result = message_handlers.handle_auc(match, 'window')
        self.assertFalse(result)
        self.assertIsNone(disc_auction.highest())
        mock_post_event.assert_not_called()

        # Someone in the alliance says random stuff with a number
        line = ("[Sun Aug 16 22:47:31 2020] Tim auctions, "
                "'I am 12 and what channel is this'")
        match = config.MATCH_AUC.match(line)
        result = message_handlers.handle_auc(match, 'window')
        self.assertFalse(result)
        self.assertIsNone(disc_auction.highest())
        mock_post_event.assert_not_called()

        # Some bad line is passed somehow
        line = "???"
        match = config.MATCH_AUC.match(line)
        result = message_handlers.handle_auc(match, 'window')
        self.assertFalse(result)
        self.assertIsNone(disc_auction.highest())
        mock_post_event.assert_not_called()

        # Someone in the alliance bids on two items at once
        line = ("[Sun Aug 16 22:47:31 2020] Jim auctions, "
                "'Copper Disc 10 DKP Platinum Disc'")
        match = config.MATCH_AUC.match(line)
        result = message_handlers.handle_auc(match, 'window')
        self.assertFalse(result)
        self.assertIsNone(disc_auction.highest())
        mock_post_event.assert_not_called()

        # Someone in the alliance bids on an active item
        line = ("[Sun Aug 16 22:47:31 2020] Jim auctions, "
                "'Copper Disc 10 DKP'")
        match = config.MATCH_AUC.match(line)
        result = message_handlers.handle_auc(match, 'window')
        self.assertTrue(result)
        self.assertIn(('Jim', 10), disc_auction.highest())
        mock_post_event.assert_called_once_with(
            'window', models.BidEvent(disc_auction))
