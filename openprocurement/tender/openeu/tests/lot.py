# -*- coding: utf-8 -*-
import unittest
from copy import deepcopy
from datetime import timedelta

from openprocurement.api.models import get_now
from openprocurement.api.tests.base import test_organization, create_classmethod
from openprocurement.api.tests.lot import BaseTenderLotFeatureResourceTest
from openprocurement.api.tests.lot_test_utils import (create_tender_lot_invalid,
                                                      patch_tender_currency,
                                                      patch_tender_vat)
from openprocurement.tender.openua.tests.lot_test_utils import (get_tender_lot,
                                                                get_tender_lots)
from openprocurement.tender.openeu.tests.lot_test_utils import (create_tender_lot,
                                                                patch_tender_lot,
                                                                delete_tender_lot,
                                                                tender_lot_guarantee)
from openprocurement.tender.openeu.tests.base import (BaseTenderContentWebTest,
                                                      BaseTenderWebTest,
                                                      test_tender_data,
                                                      test_lots,
                                                      test_bids)

# from openprocurement.api.tests.base import BaseWebTest, BaseTenderWebTest, test_tender_data, test_lots


class BaseTenderLotResourceTest(object):

    test_create_tender_lot_invalid = create_classmethod(create_tender_lot_invalid)
    test_patch_tender_currency = create_classmethod(patch_tender_currency)
    test_patch_tender_vat = create_classmethod(patch_tender_vat)
    test_get_tender_lot = create_classmethod(get_tender_lot)
    test_get_tender_lots = create_classmethod(get_tender_lots)
    test_create_tender_lot = create_classmethod(create_tender_lot)
    test_patch_tender_lot = create_classmethod(patch_tender_lot)
    test_delete_tender_lot = create_classmethod(delete_tender_lot)
    test_tender_lot_guarantee = create_classmethod(tender_lot_guarantee)

class TenderLotResourceTest(BaseTenderContentWebTest,
                            BaseTenderLotResourceTest):
    initial_auth = ('Basic', ('broker', ''))
    test_tender_data = test_tender_data

class TenderLotEdgeCasesTest(BaseTenderContentWebTest):
    initial_auth = ('Basic', ('broker', ''))
    initial_lots = test_lots * 2
    initial_bids = test_bids

    def test_question_blocking(self):

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/questions'.format(self.tender_id),
                                      {'data': {'title': 'question title',
                                                'description': 'question description',
                                                'questionOf': 'lot',
                                                'relatedItem': self.initial_lots[0]['id'],
                                                'author': test_organization}})
        question = response.json['data']
        self.assertEqual(question['questionOf'], 'lot')
        self.assertEqual(question['relatedItem'], self.initial_lots[0]['id'])

        self.set_status('active.pre-qualification', extra={"status": "active.tendering"})
        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.json['data']['status'], 'active.tendering')

        # cancel lot
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': {'reason': 'cancellation reason',
                                                'status': 'active',
                                                "cancellationOf": "lot",
                                                "relatedLot": self.initial_lots[0]['id']}})

        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {"data": {"id": self.tender_id}})

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.json['data']['status'], 'active.pre-qualification')

    def test_claim_blocking(self):
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/complaints'.format(self.tender_id),
                                      {'data': {'title': 'complaint title',
                                                'description': 'complaint description',
                                                'author': test_organization,
                                                'relatedLot': self.initial_lots[0]['id'],
                                                'status': 'claim'}})
        self.assertEqual(response.status, '201 Created')
        complaint = response.json['data']
        owner_token = response.json['access']['token']
        self.assertEqual(complaint['relatedLot'], self.initial_lots[0]['id'])

        self.set_status('active.auction', extra={"status": "active.tendering"})
        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.json['data']['status'], 'active.tendering')

        # cancel lot
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': {'reason': 'cancellation reason',
                                                'status': 'active',
                                                "cancellationOf": "lot",
                                                "relatedLot": self.initial_lots[0]['id']}})

        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {"data": {"id": self.tender_id}})

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.json['data']['status'], 'active.pre-qualification')

    def test_next_check_value_with_unanswered_question(self):
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/questions'.format(self.tender_id),
                                      {'data': {'title': 'question title',
                                                'description': 'question description',
                                                'questionOf': 'lot',
                                                'relatedItem': self.initial_lots[0]['id'],
                                                'author': test_organization}})
        question = response.json['data']
        self.assertEqual(question['questionOf'], 'lot')
        self.assertEqual(question['relatedItem'], self.initial_lots[0]['id'])

        self.set_status('active.pre-qualification', extra={"status": "active.tendering"})
        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], 'active.tendering')
        self.assertNotIn('next_check', response.json['data'])

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': {'reason': 'cancellation reason',
                                                'status': 'active',
                                                "cancellationOf": "lot",
                                                "relatedLot": self.initial_lots[0]['id']}})

        response = self.app.get('/tenders/{}'.format(self.tender_id, ))
        self.assertIn('next_check', response.json['data'])
        self.assertEqual(response.json['data']['next_check'], response.json['data']['tenderPeriod']['endDate'])

        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], 'active.pre-qualification')

    def test_next_check_value_with_unanswered_claim(self):
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/complaints'.format(self.tender_id),
                                      {'data': {'title': 'complaint title',
                                                'description': 'complaint description',
                                                'author': test_organization,
                                                'relatedLot': self.initial_lots[0]['id'],
                                                'status': 'claim'}})
        self.assertEqual(response.status, '201 Created')
        complaint = response.json['data']
        owner_token = response.json['access']['token']
        self.assertEqual(complaint['relatedLot'], self.initial_lots[0]['id'])

        self.set_status('active.auction', extra={"status": "active.tendering"})
        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], 'active.tendering')
        self.assertNotIn('next_check', response.json['data'])

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': {'reason': 'cancellation reason',
                                                'status': 'active',
                                                "cancellationOf": "lot",
                                                "relatedLot": self.initial_lots[0]['id']}})

        response = self.app.get('/tenders/{}'.format(self.tender_id, ))
        self.assertIn('next_check', response.json['data'])
        self.assertEqual(response.json['data']['next_check'], response.json['data']['tenderPeriod']['endDate'])

        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], 'active.pre-qualification')


class TenderLotFeatureResourceTest(BaseTenderContentWebTest,
                                   BaseTenderLotFeatureResourceTest):
    initial_lots = 2 * test_lots
    initial_auth = ('Basic', ('broker', ''))
    test_tender_data = test_tender_data



class TenderLotBidderResourceTest(BaseTenderContentWebTest):
    initial_lots = test_lots
    initial_auth = ('Basic', ('broker', ''))

    def test_create_tender_bidder_invalid(self):
        request_path = '/tenders/{}/bids'.format(self.tender_id)
        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True, 'tenderers': test_bids[0]['tenderers']}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u'This field is required.'], u'location': u'body', u'name': u'lotValues'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True, 'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500}}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'relatedLot': [u'This field is required.']}], u'location': u'body', u'name': u'lotValues'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True, 'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': "0" * 32}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'relatedLot': [u'relatedLot should be one of lots']}], u'location': u'body', u'name': u'lotValues'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True, 'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 5000000}, 'relatedLot': self.initial_lots[0]['id']}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'value': [u'value of bid should be less than value of lot']}], u'location': u'body', u'name': u'lotValues'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True, 'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500, 'valueAddedTaxIncluded': False}, 'relatedLot': self.initial_lots[0]['id']}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'value': [u'valueAddedTaxIncluded of bid should be identical to valueAddedTaxIncluded of value of lot']}], u'location': u'body', u'name': u'lotValues'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True, 'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500, 'currency': "USD"}, 'relatedLot': self.initial_lots[0]['id']}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'value': [u'currency of bid should be identical to currency of value of lot']}], u'location': u'body', u'name': u'lotValues'},
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True, 'tenderers': test_bids[0]['tenderers'], "value": {"amount": 500}, 'lotValues': [{"value": {"amount": 500}, 'relatedLot': self.initial_lots[0]['id']}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u'value should be posted for each lot of bid'], u'location': u'body', u'name': u'value'}
        ])

    def test_patch_tender_bidder(self):
        lot_id = self.initial_lots[0]['id']
        response = self.app.post_json('/tenders/{}/bids'.format(self.tender_id), {'data': {'selfEligible': True, 'selfQualified': True, 'tenderers': test_bids[0]["tenderers"], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': lot_id}]}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        bidder = response.json['data']
        bid_token = response.json['access']['token']
        lot = bidder['lotValues'][0]

        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bidder['id'], bid_token), {"data": {'tenderers': [{"name": u"Державне управління управлінням справами"}]}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['lotValues'][0]['date'], lot['date'])
        self.assertNotEqual(response.json['data']['tenderers'][0]['name'], bidder['tenderers'][0]['name'])

        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bidder['id'], bid_token), {"data": {'lotValues': [{"value": {"amount": 500}, 'relatedLot': lot_id}], 'tenderers': test_bids[0]["tenderers"]}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['lotValues'][0]['date'], lot['date'])
        self.assertEqual(response.json['data']['tenderers'][0]['name'], bidder['tenderers'][0]['name'])

        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bidder['id'], bid_token), {"data": {'lotValues': [{"value": {"amount": 400}, 'relatedLot': lot_id}]}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['lotValues'][0]["value"]["amount"], 400)
        self.assertNotEqual(response.json['data']['lotValues'][0]['date'], lot['date'])

        self.time_shift('active.pre-qualification')
        self.check_chronograph()

        response = self.app.get('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bidder['id'], bid_token))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertNotIn('lotValues', response.json['data'])

        response = self.app.patch_json('/tenders/{}/bids/{}?acc_token={}'.format(self.tender_id, bidder['id'], bid_token), {"data": {'lotValues': [{"value": {"amount": 500}, 'relatedLot': lot_id}], 'status': 'active'}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Can't update bid in current (unsuccessful) tender status")


class TenderLotFeatureBidderResourceTest(BaseTenderContentWebTest):
    initial_lots = test_lots
    initial_auth = ('Basic', ('broker', ''))

    def setUp(self):
        super(TenderLotFeatureBidderResourceTest, self).setUp()
        self.lot_id = self.initial_lots[0]['id']
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token), {"data": {
            "items": [
                {
                    'relatedLot': self.lot_id,
                    'id': '1'
                }
            ],
            "features": [
                {
                    "code": "code_item",
                    "featureOf": "item",
                    "relatedItem": "1",
                    "title": u"item feature",
                    "enum": [
                        {
                            "value": 0.01,
                            "title": u"good"
                        },
                        {
                            "value": 0.02,
                            "title": u"best"
                        }
                    ]
                },
                {
                    "code": "code_lot",
                    "featureOf": "lot",
                    "relatedItem": self.lot_id,
                    "title": u"lot feature",
                    "enum": [
                        {
                            "value": 0.01,
                            "title": u"good"
                        },
                        {
                            "value": 0.02,
                            "title": u"best"
                        }
                    ]
                },
                {
                    "code": "code_tenderer",
                    "featureOf": "tenderer",
                    "title": u"tenderer feature",
                    "enum": [
                        {
                            "value": 0.01,
                            "title": u"good"
                        },
                        {
                            "value": 0.02,
                            "title": u"best"
                        }
                    ]
                }
            ]
        }})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['items'][0]['relatedLot'], self.lot_id)

    def test_create_tender_bidder_invalid(self):
        request_path = '/tenders/{}/bids'.format(self.tender_id)
        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True, 'tenderers': test_bids[0]['tenderers']}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True, 'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500}}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'relatedLot': [u'This field is required.']}], u'location': u'body', u'name': u'lotValues'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True, 'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': "0" * 32}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'relatedLot': [u'relatedLot should be one of lots']}], u'location': u'body', u'name': u'lotValues'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True,
                                                              'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 5000000}, 'relatedLot': self.lot_id}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'value': [u'value of bid should be less than value of lot']}], u'location': u'body', u'name': u'lotValues'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True,
                                                              'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500, 'valueAddedTaxIncluded': False}, 'relatedLot': self.lot_id}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'value': [u'valueAddedTaxIncluded of bid should be identical to valueAddedTaxIncluded of value of lot']}], u'location': u'body', u'name': u'lotValues'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True,
                                                              'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500, 'currency': "USD"}, 'relatedLot': self.lot_id}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'value': [u'currency of bid should be identical to currency of value of lot']}], u'location': u'body', u'name': u'lotValues'},
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True,
                                                              'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': self.lot_id}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True,
                                                              'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': self.lot_id}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u'All features parameters is required.'], u'location': u'body', u'name': u'parameters'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True,
                                                              'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': self.lot_id}], 'parameters': [{"code": "code_item", "value": 0.01}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u'All features parameters is required.'], u'location': u'body', u'name': u'parameters'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True,
                                                              'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': self.lot_id}], 'parameters': [{"code": "code_invalid", "value": 0.01}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'code': [u'code should be one of feature code.']}], u'location': u'body', u'name': u'parameters'}
        ])

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True,
                                                              'tenderers': test_bids[0]['tenderers'], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': self.lot_id}], 'parameters': [
            {"code": "code_item", "value": 0.01},
            {"code": "code_tenderer", "value": 0},
            {"code": "code_lot", "value": 0.01},
        ]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'value': [u'value should be one of feature value.']}], u'location': u'body', u'name': u'parameters'}
        ])

    def test_create_tender_bidder(self):
        request_path = '/tenders/{}/bids'.format(self.tender_id)
        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True,
                                                              'tenderers': test_bids[0]["tenderers"], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': self.lot_id}], 'parameters': [
            {"code": "code_item", "value": 0.01},
            {"code": "code_tenderer", "value": 0.01},
            {"code": "code_lot", "value": 0.01},
        ]}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        bidder = response.json['data']
        self.assertEqual(bidder['tenderers'][0]['name'], test_tender_data["procuringEntity"]['name'])
        self.assertIn('id', bidder)
        self.assertIn(bidder['id'], response.headers['Location'])

        self.time_shift('active.pre-qualification')
        self.check_chronograph()

        response = self.app.post_json(request_path, {'data': {'selfEligible': True, 'selfQualified': True,
                                                              'tenderers': test_bids[0]["tenderers"], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': self.lot_id}], 'parameters': [
            {"code": "code_item", "value": 0.01},
            {"code": "code_tenderer", "value": 0.01},
            {"code": "code_lot", "value": 0.01},
        ]}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Can't add bid in current (unsuccessful) tender status")


class TenderLotProcessTest(BaseTenderContentWebTest):
    setUp = BaseTenderContentWebTest.setUp


    def test_1lot_0bid(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        # add lot
        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
        self.assertEqual(response.status, '201 Created')
        lot_id = response.json['data']['id']
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': lot_id}]}})
        self.assertEqual(response.status, '200 OK')
        # switch to active.tendering
        response = self.set_status('active.tendering', {"lots": [{"auctionPeriod": {"startDate": (get_now() + timedelta(days=10)).isoformat()}}]})
        self.assertIn("auctionPeriod", response.json['data']['lots'][0])
        # switch to unsuccessful
        response = self.set_status('active.auction', {"lots": [{"auctionPeriod": {"startDate": None}}], 'status': 'active.tendering'})
        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(tender_id), {"data": {"id": tender_id}})
        self.assertEqual(response.json['data']["lots"][0]['status'], 'unsuccessful')
        self.assertEqual(response.json['data']['status'], 'unsuccessful')

        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'], [{
            "location": "body", "name": "data", "description": "Can't add lot in current (unsuccessful) tender status"
        }])

    def test_1lot_1bid(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        # add lot
        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
        self.assertEqual(response.status, '201 Created')
        lot_id = response.json['data']['id']
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': lot_id}]}})
        self.assertEqual(response.status, '200 OK')
        # create bid
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id),
                                      {'data': {'selfEligible': True, 'selfQualified': True,
                                                'tenderers': test_bids[0]["tenderers"], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': lot_id}]}})
        # switch to active.pre-qualification
        self.time_shift('active.pre-qualification')
        self.check_chronograph()
        # switch to unsuccessful
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}?acc_token={}'.format(tender_id, owner_token))
        self.assertEqual(response.json['data']['status'], 'unsuccessful')

    def test_1lot_2bid_1unqualified(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        # add lot
        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
        self.assertEqual(response.status, '201 Created')
        lot_id = response.json['data']['id']
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': lot_id}]}})
        self.assertEqual(response.status, '200 OK')
        # create bid
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id),
                                      {'data': {'selfEligible': True, 'selfQualified': True,
                                                'tenderers': test_bids[0]["tenderers"], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': lot_id}]}})

        response = self.app.post_json('/tenders/{}/bids'.format(tender_id),
                                      {'data': {'selfEligible': True, 'selfQualified': True,
                                                'tenderers': test_bids[1]["tenderers"], 'lotValues': [{"value": {"amount": 500}, 'relatedLot': lot_id}]}})
        # switch to active.pre-qualification
        self.time_shift('active.pre-qualification')
        self.check_chronograph()

        response = self.app.get('/tenders/{}/qualifications?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        qualifications = response.json['data']

        response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualifications[0]['id'], owner_token),
                                  {"data": {'status': 'active', "qualified": True, "eligible": True}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'active')

        response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualifications[1]['id'], owner_token),
                                  {"data": {'status': 'unsuccessful'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'unsuccessful')
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token),
                                       {"data": {"status": "active.pre-qualification.stand-still"}})

        self.assertEqual(response.status, "200 OK")
        self.assertEqual(response.json['data']['status'], "active.pre-qualification.stand-still")

        self.set_status('active.auction', {"id": tender_id, 'status': 'active.pre-qualification.stand-still'})
        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(tender_id), {"data": {"id": tender_id}})
        self.assertEqual(response.status, "200 OK")
        self.assertEqual(response.json['data']['status'], "unsuccessful")


    def test_1lot_2bid(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        # add lot
        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
        self.assertEqual(response.status, '201 Created')
        lot_id = response.json['data']['id']
        self.initial_lots = [response.json['data']]
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': lot_id}]}})
        self.assertEqual(response.status, '200 OK')
        # create bid
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id),
                                      {'data': {'selfEligible': True, 'selfQualified': True,
                                                'tenderers': test_bids[0]["tenderers"], 'lotValues': [{"value": {"amount": 450}, 'relatedLot': lot_id}]}})
        bid_id = response.json['data']['id']
        bid_token = response.json['access']['token']
        # create second bid
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id),
                                      {'data': {'selfEligible': True, 'selfQualified': True,
                                                'tenderers': test_bids[1]["tenderers"], 'lotValues': [{"value": {"amount": 475}, 'relatedLot': lot_id}]}})
        # switch to active.auction
        self.time_shift('active.pre-qualification')
        self.check_chronograph()

        response = self.app.get('/tenders/{}/qualifications?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        qualifications = response.json['data']
        for qualification in qualifications:
            response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualification['id'], owner_token),
                                      {"data": {'status': 'active', "qualified": True, "eligible": True}})
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(response.json['data']['status'], 'active')

        response = self.app.get('/tenders/{}?acc_token={}'.format(tender_id, owner_token))
        self.assertEqual(response.status, '200 OK')

        for bid in response.json['data']['bids']:
            self.assertEqual(bid['status'], 'active')

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token),
                                       {"data": {"status": "active.pre-qualification.stand-still"}})
        self.assertEqual(response.status, "200 OK")
        self.check_chronograph()

        response = self.app.get('/tenders/{}?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.status, "200 OK")

        self.time_shift('active.auction')

        self.check_chronograph()

        # get auction info
        self.app.authorization = ('Basic', ('auction', ''))
        response = self.app.get('/tenders/{}/auction'.format(tender_id))
        auction_bids_data = response.json['data']['bids']
        # posting auction urls
        response = self.app.patch_json('/tenders/{}/auction/{}'.format(tender_id, lot_id), {
            'data': {
                'lots': [
                    {
                        'id': i['id'],
                        'auctionUrl': 'https://tender.auction.url'
                    }
                    for i in response.json['data']['lots']
                ],
                'bids': [
                    {
                        'id': i['id'],
                        'lotValues': [
                            {
                                'relatedLot': j['relatedLot'],
                                'participationUrl': 'https://tender.auction.url/for_bid/{}'.format(i['id'])
                            }
                            for j in i['lotValues']
                        ],
                    }
                    for i in auction_bids_data
                ]
            }
        })
        # view bid participationUrl
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/bids/{}?acc_token={}'.format(tender_id, bid_id, bid_token))
        self.assertEqual(response.json['data']['lotValues'][0]['participationUrl'], 'https://tender.auction.url/for_bid/{}'.format(bid_id))
        # posting auction results
        self.app.authorization = ('Basic', ('auction', ''))
        response = self.app.post_json('/tenders/{}/auction/{}'.format(tender_id, lot_id), {'data': {'bids': auction_bids_data}})
        # # get awards
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending'][0]
        # set award as active
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"status": "active", "qualified": True, "eligible": True}})
        # get contract id
        response = self.app.get('/tenders/{}'.format(tender_id))
        contract_id = response.json['data']['contracts'][-1]['id']
        # after stand slill period

        self.time_shift('complete')
        self.check_chronograph()

        # # time travel
        tender = self.db.get(tender_id)
        for i in tender.get('awards', []):
            i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)
        # # sign contract
        self.app.authorization = ('Basic', ('broker', ''))
        self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(tender_id, contract_id, owner_token), {"data": {"status": "active"}})
        # check status
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.json['data']["lots"][0]['status'], 'complete')
        self.assertEqual(response.json['data']['status'], 'complete')

    def test_2lot_2bid_1lot_del(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        lots = []
        for lot in 2 * test_lots:
            # add lot
            response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
            self.assertEqual(response.status, '201 Created')
            lots.append(response.json['data']['id'])
        self.initial_lots = lots
        # add item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [test_tender_data['items'][0] for i in lots]}})

        response = self.set_status('active.tendering', {"lots": [
            {"auctionPeriod": {"startDate": (get_now() + timedelta(days=16)).isoformat()}}
            for i in lots
        ]})
        # create bid

        bids = []
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id), {'data': {'selfEligible': True, 'selfQualified': True,
                                                                                      'tenderers': test_bids[0]["tenderers"], 'lotValues': [
            {"value": {"amount": 500}, 'relatedLot': lot_id}
            for lot_id in lots
        ]}})
        bids.append(response.json)
        # create second bid
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id), {'data': {'selfEligible': True, 'selfQualified': True,
                                                                                      'tenderers': test_bids[1]["tenderers"], 'lotValues': [
            {"value": {"amount": 500}, 'relatedLot': lot_id}
            for lot_id in lots
        ]}})
        bids.append(response.json)
        response = self.app.delete('/tenders/{}/lots/{}?acc_token={}'.format(self.tender_id, lots[0], owner_token))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')

    def test_1lot_3bid_1del(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        # add lot
        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
        self.assertEqual(response.status, '201 Created')
        lot_id = response.json['data']['id']
        self.initial_lots = [response.json['data']]
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': lot_id}]}})
        self.assertEqual(response.status, '200 OK')
        # create bid
        self.app.authorization = ('Basic', ('broker', ''))
        bids = []
        for i in range(3):
            response = self.app.post_json('/tenders/{}/bids'.format(tender_id),
                                          {'data': {'selfEligible': True, 'selfQualified': True,
                                                    'tenderers': test_bids[0]["tenderers"], 'lotValues': [{"value": {"amount": 450}, 'relatedLot': lot_id}]}})
            bids.append({response.json['data']['id']: response.json['access']['token']})


        response = self.app.delete('/tenders/{}/bids/{}?acc_token={}'.format(tender_id, bids[2].keys()[0], bids[2].values()[0]))
        self.assertEqual(response.status, '200 OK')
        # switch to active.auction
        self.time_shift('active.pre-qualification')
        self.check_chronograph()

        response = self.app.get('/tenders/{}/qualifications?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        qualifications = response.json['data']

        for qualification in qualifications:
            response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualification['id'], owner_token),
                                      {"data": {'status': 'active', "qualified": True, "eligible": True}})
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(response.json['data']['status'], 'active')
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token),
                                       {"data": {"status": "active.pre-qualification.stand-still"}})
        self.assertEqual(response.status, "200 OK")
        self.check_chronograph()

        response = self.app.get('/tenders/{}?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.status, "200 OK")

        response = self.app.get('/tenders/{}/qualifications?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        qualifications = response.json['data']

        self.time_shift('active.auction')

        self.check_chronograph()
        # get auction info
        self.app.authorization = ('Basic', ('auction', ''))
        response = self.app.get('/tenders/{}/auction'.format(tender_id))
        auction_bids_data = response.json['data']['bids']
        # posting auction urls
        data ={
            'data': {
                'lots': [
                    {
                        'id': i['id'],
                        'auctionUrl': 'https://tender.auction.url'
                    }
                    for i in response.json['data']['lots']
                ],
                'bids': list(auction_bids_data)
            }
        }

        for bid_index, bid in enumerate(auction_bids_data):
            if bid.get('status', 'active') == 'active':
                for lot_index, lot_bid in enumerate(bid['lotValues']):
                    if lot_bid['relatedLot'] == lot_id and lot_bid.get('status', 'active') == 'active':
                        data['data']['bids'][bid_index]['lotValues'][lot_index]['participationUrl'] = 'https://tender.auction.url/for_bid/{}'.format(bid['id'])
                        break

        response = self.app.patch_json('/tenders/{}/auction/{}'.format(tender_id, lot_id), data)
        # view bid participationUrl
        self.app.authorization = ('Basic', ('broker', ''))
        bid_id = bids[0].keys()[0]
        bid_token = bids[0].values()[0]
        response = self.app.get('/tenders/{}/bids/{}?acc_token={}'.format(tender_id, bid_id, bid_token))
        self.assertEqual(response.json['data']['lotValues'][0]['participationUrl'], 'https://tender.auction.url/for_bid/{}'.format(bid_id))

        bid_id = bids[2].keys()[0]
        bid_token = bids[2].values()[0]
        response = self.app.get('/tenders/{}/bids/{}?acc_token={}'.format(tender_id, bid_id, bid_token))
        self.assertEqual(response.json['data']['status'], 'deleted')

        # posting auction results
        self.app.authorization = ('Basic', ('auction', ''))
        response = self.app.post_json('/tenders/{}/auction/{}'.format(tender_id, lot_id), {'data': {'bids': auction_bids_data}})
        # # get awards
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending'][0]
        # set award as active
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"status": "active", "qualified": True, "eligible": True}})
        # get contract id
        response = self.app.get('/tenders/{}'.format(tender_id))
        contract_id = response.json['data']['contracts'][-1]['id']
        # after stand slill period

        self.time_shift('complete')
        self.check_chronograph()

        # # time travel
        tender = self.db.get(tender_id)
        for i in tender.get('awards', []):
            i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)
        # # sign contract
        self.app.authorization = ('Basic', ('broker', ''))
        self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(tender_id, contract_id, owner_token), {"data": {"status": "active"}})
        # check status
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.json['data']["lots"][0]['status'], 'complete')
        self.assertEqual(response.json['data']['status'], 'complete')


    def test_1lot_3bid_1un(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        # add lot
        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
        self.assertEqual(response.status, '201 Created')
        lot_id = response.json['data']['id']
        self.initial_lots = [response.json['data']]
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': lot_id}]}})
        self.assertEqual(response.status, '200 OK')
        # create bid
        self.app.authorization = ('Basic', ('broker', ''))
        bids = []
        for i in range(3):
            response = self.app.post_json('/tenders/{}/bids'.format(tender_id),
                                          {'data': {'selfEligible': True, 'selfQualified': True,
                                                    'tenderers': test_bids[0]["tenderers"], 'lotValues': [{"value": {"amount": 450}, 'relatedLot': lot_id}]}})
            bids.append({response.json['data']['id']: response.json['access']['token']})

        # switch to active.auction
        self.time_shift('active.pre-qualification')
        self.check_chronograph()

        response = self.app.get('/tenders/{}/qualifications?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        qualifications = response.json['data']
        for qualification in qualifications:
            if qualification['bidID'] == bids[2].keys()[0]:
                response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualification['id'], owner_token),
                                          {"data": {'status': 'unsuccessful'}})
                self.assertEqual(response.status, '200 OK')
                self.assertEqual(response.json['data']['status'], 'unsuccessful')
            else:
                response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualification['id'], owner_token),
                                          {"data": {'status': 'active', "qualified": True, "eligible": True}})
                self.assertEqual(response.status, '200 OK')
                self.assertEqual(response.json['data']['status'], 'active')
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token),
                                       {"data": {"status": "active.pre-qualification.stand-still"}})
        self.assertEqual(response.status, "200 OK")
        self.check_chronograph()

        response = self.app.get('/tenders/{}?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.status, "200 OK")

        response = self.app.get('/tenders/{}/qualifications?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        qualifications = response.json['data']

        self.time_shift('active.auction')

        self.check_chronograph()
        # get auction info
        self.app.authorization = ('Basic', ('auction', ''))
        response = self.app.get('/tenders/{}/auction'.format(tender_id))
        auction_bids_data = response.json['data']['bids']
        # posting auction urls
        data ={
            'data': {
                'lots': [
                    {
                        'id': i['id'],
                        'auctionUrl': 'https://tender.auction.url'
                    }
                    for i in response.json['data']['lots']
                ],
                'bids': list(auction_bids_data)
            }
        }

        for bid_index, bid in enumerate(auction_bids_data):
            if bid.get('status', 'active') == 'active':
                for lot_index, lot_bid in enumerate(bid['lotValues']):
                    if lot_bid['relatedLot'] == lot_id and lot_bid.get('status', 'active') == 'active':
                        data['data']['bids'][bid_index]['lotValues'][lot_index]['participationUrl'] = 'https://tender.auction.url/for_bid/{}'.format(bid['id'])
                        break

        response = self.app.patch_json('/tenders/{}/auction/{}'.format(tender_id, lot_id), data)
        # view bid participationUrl
        self.app.authorization = ('Basic', ('broker', ''))
        bid_id = bids[0].keys()[0]
        bid_token = bids[0].values()[0]
        response = self.app.get('/tenders/{}/bids/{}?acc_token={}'.format(tender_id, bid_id, bid_token))
        self.assertEqual(response.json['data']['lotValues'][0]['participationUrl'], 'https://tender.auction.url/for_bid/{}'.format(bid_id))

        bid_id = bids[2].keys()[0]
        bid_token = bids[2].values()[0]
        response = self.app.get('/tenders/{}/bids/{}?acc_token={}'.format(tender_id, bid_id, bid_token))
        self.assertNotIn('lotValues', response.json['data'])

        # posting auction results
        self.app.authorization = ('Basic', ('auction', ''))
        response = self.app.post_json('/tenders/{}/auction/{}'.format(tender_id, lot_id), {'data': {'bids': auction_bids_data}})
        # # get awards
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending'][0]
        # set award as active
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"status": "active", "qualified": True, "eligible": True}})
        # get contract id
        response = self.app.get('/tenders/{}'.format(tender_id))
        contract_id = response.json['data']['contracts'][-1]['id']
        # after stand slill period

        self.time_shift('complete')
        self.check_chronograph()

        # # time travel
        tender = self.db.get(tender_id)
        for i in tender.get('awards', []):
            i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)
        # # sign contract
        self.app.authorization = ('Basic', ('broker', ''))
        self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(tender_id, contract_id, owner_token), {"data": {"status": "active"}})
        # check status
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.json['data']["lots"][0]['status'], 'complete')
        self.assertEqual(response.json['data']['status'], 'complete')

    def test_2lot_0bid(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        lots = []
        for lot in 2 * test_lots:
            # add lot
            response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
            self.assertEqual(response.status, '201 Created')
            lots.append(response.json['data']['id'])
        # add item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [test_tender_data['items'][0] for i in lots]}})
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': i} for i in lots]}})
        self.assertEqual(response.status, '200 OK')

        self.time_shift('active.pre-qualification')
        self.check_chronograph()
        # switch to unsuccessful
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}?acc_token={}'.format(tender_id, owner_token))
        self.assertTrue(all([i['status'] == 'unsuccessful' for i in response.json['data']['lots']]))
        self.assertEqual(response.json['data']['status'], 'unsuccessful')

    def test_2lot_2can(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        lots = []
        for lot in 2 * test_lots:
            # add lot
            response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
            self.assertEqual(response.status, '201 Created')
            lots.append(response.json['data']['id'])
        # add item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [test_tender_data['items'][0] for i in lots]}})
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': i} for i in lots]}})
        self.assertEqual(response.status, '200 OK')
        # cancel every lot
        for lot_id in lots:
            response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(tender_id, owner_token), {'data': {
                'reason': 'cancellation reason',
                'status': 'active',
                "cancellationOf": "lot",
                "relatedLot": lot_id
            }})
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertTrue(all([i['status'] == 'cancelled' for i in response.json['data']['lots']]))
        self.assertEqual(response.json['data']['status'], 'cancelled')

    def test_2lot_1can(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        lots = []
        for lot in 2 * test_lots:
            # add lot
            response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
            self.assertEqual(response.status, '201 Created')
            lots.append(response.json['data']['id'])
        # add item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [test_tender_data['items'][0] for i in lots]}})
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': i} for i in lots]}})
        self.assertEqual(response.status, '200 OK')
        # cancel first lot
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(tender_id, owner_token), {'data': {
            'reason': 'cancellation reason',
            'status': 'active',
            "cancellationOf": "lot",
            "relatedLot": lots[0]
        }})

        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertFalse(all([i['status'] == 'cancelled' for i in response.json['data']['lots']]))
        self.assertTrue(any([i['status'] == 'cancelled' for i in response.json['data']['lots']]))
        self.assertEqual(response.json['data']['status'], 'active.tendering')

        # try to restore lot back by old cancellation
        response = self.app.get('/tenders/{}/cancellations?acc_token={}'.format(tender_id, owner_token))
        self.assertEqual(len(response.json['data']), 1)
        cancellation = response.json['data'][0]
        self.assertEqual(cancellation['status'], 'active')

        response = self.app.patch_json('/tenders/{}/cancellations/{}?acc_token={}'.format(tender_id, cancellation['id'], owner_token),
                                      {'data': {'status': 'pending'}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'][0]["description"], "Can update cancellation only in active lot status")

        # try to restore lot back by new pending cancellation
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(tender_id, owner_token), {'data': {
            'reason': 'cancellation reason',
            'status': 'pending',
            "cancellationOf": "lot",
            "relatedLot": lots[0]
        }}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'][0]["description"], "Can add cancellation only in active lot status")
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertFalse(all([i['status'] == 'cancelled' for i in response.json['data']['lots']]))
        self.assertTrue(any([i['status'] == 'cancelled' for i in response.json['data']['lots']]))
        self.assertEqual(response.json['data']['status'], 'active.tendering')

    def test_2lot_2bid_0com_1can(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        lots = []
        for lot in 2 * test_lots:
            # add lot
            response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
            self.assertEqual(response.status, '201 Created')
            lots.append(response.json['data']['id'])
        # add item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [test_tender_data['items'][0] for i in lots]}})
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': i} for i in lots]}})
        self.assertEqual(response.status, '200 OK')
        # create bid
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id), {'data': {'selfEligible': True, 'selfQualified': True,
                                                                                      'tenderers': test_bids[0]['tenderers'], 'lotValues': [
            {"value": {"amount": 500}, 'relatedLot': lot_id}
            for lot_id in lots
        ]}})

        response = self.app.post_json('/tenders/{}/bids'.format(tender_id), {'data': {'selfEligible': True, 'selfQualified': True,
                                                                                      'tenderers': test_bids[1]['tenderers'], 'lotValues': [
            {"value": {"amount": 499}, 'relatedLot': lot_id}
            for lot_id in lots
        ]}})

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(tender_id, owner_token), {'data': {
            'reason': 'cancellation reason',
            'status': 'active',
            "cancellationOf": "lot",
            "relatedLot": lots[0]
        }})
        response = self.app.get('/tenders/{}?acc_token={}'.format(tender_id, owner_token))
        self.assertEqual(response.status, "200 OK")
        # active.pre-qualification
        self.time_shift('active.pre-qualification')
        self.check_chronograph()

        response = self.app.get('/tenders/{}/qualifications?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        qualifications = response.json['data']
        self.assertEqual(len(qualifications), 2)

        for qualification in qualifications:
            response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualification['id'], owner_token),
                                      {"data": {'status': 'active', "qualified": True, "eligible": True}})
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(response.json['data']['status'], 'active')
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token),
                                       {"data": {"status": "active.pre-qualification.stand-still"}})
        self.assertEqual(response.status, "200 OK")


    def test_2lot_2bid_2com_2win(self):
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        lots = []
        for lot in 2 * test_lots:
            # add lot
            response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
            self.assertEqual(response.status, '201 Created')
            lots.append(response.json['data']['id'])
        self.initial_lots = lots
        # add item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [test_tender_data['items'][0] for i in lots]}})
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': i} for i in lots]}})
        self.assertEqual(response.status, '200 OK')
        # create bid
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id), {'data': {'selfEligible': True, 'selfQualified': True,
                                                                                      'tenderers': test_bids[0]['tenderers'], 'lotValues': [
            {"value": {"amount": 500}, 'relatedLot': lot_id}
            for lot_id in lots
        ]}})
        # create second bid
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id), {'data': {'selfEligible': True, 'selfQualified': True,
                                                                                      'tenderers': test_bids[1]['tenderers'], 'lotValues': [
            {"value": {"amount": 500}, 'relatedLot': lot_id}
            for lot_id in lots
        ]}})
        # switch to active.pre-qualification
        self.time_shift('active.pre-qualification')
        self.check_chronograph()
        response = self.app.get('/tenders/{}/qualifications?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        qualifications = response.json['data']
        self.assertEqual(len(qualifications), 4)

        for qualification in qualifications:
            response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualification['id'], owner_token),
                                      {"data": {'status': 'active', "qualified": True, "eligible": True}})
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(response.json['data']['status'], 'active')
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token),
                                       {"data": {"status": "active.pre-qualification.stand-still"}})
        self.assertEqual(response.status, "200 OK")
        # switch to active.auction
        self.time_shift('active.auction')
        self.check_chronograph()
        # get auction info
        self.app.authorization = ('Basic', ('auction', ''))
        response = self.app.get('/tenders/{}/auction'.format(tender_id))
        auction_bids_data = response.json['data']['bids']
        for lot_id in lots:
            # posting auction urls
            response = self.app.patch_json('/tenders/{}/auction/{}'.format(tender_id, lot_id), {
                'data': {
                    'lots': [
                        {
                            'id': i['id'],
                            'auctionUrl': 'https://tender.auction.url'
                        }
                        for i in response.json['data']['lots']
                    ],
                    'bids': [
                        {
                            'id': i['id'],
                            'lotValues': [
                                {
                                    'relatedLot': j['relatedLot'],
                                    'participationUrl': 'https://tender.auction.url/for_bid/{}'.format(i['id'])
                                }
                                for j in i['lotValues']
                            ],
                        }
                        for i in auction_bids_data
                    ]
                }
            })
            # posting auction results
            self.app.authorization = ('Basic', ('auction', ''))
            response = self.app.post_json('/tenders/{}/auction/{}'.format(tender_id, lot_id), {'data': {'bids': auction_bids_data}})
        # for first lot
        lot_id = lots[0]
        # get awards
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending' and i['lotID'] == lot_id][0]
        # set award as active
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"status": "active", "qualified": True, "eligible": True}})
        # get contract id
        response = self.app.get('/tenders/{}'.format(tender_id))
        contract_id = response.json['data']['contracts'][-1]['id']
        # after stand slill period
        self.set_status('complete', {'status': 'active.awarded'})
        # time travel
        tender = self.db.get(tender_id)
        for i in tender.get('awards', []):
            i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)
        # sign contract
        self.app.authorization = ('Basic', ('broker', ''))
        self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(tender_id, contract_id, owner_token), {"data": {"status": "active"}})
        # for second lot
        lot_id = lots[1]
        # get awards
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending' and i['lotID'] == lot_id][0]
        # set award as unsuccessful
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"status": "unsuccessful"}})
        # get awards
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending' and i['lotID'] == lot_id][0]
        # set award as active
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"status": "active", "qualified": True, "eligible": True}})
        # get contract id
        response = self.app.get('/tenders/{}'.format(tender_id))
        contract_id = response.json['data']['contracts'][-1]['id']
        # after stand slill period
        self.set_status('complete', {'status': 'active.awarded'})
        # time travel
        tender = self.db.get(tender_id)
        for i in tender.get('awards', []):
            i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)
        # sign contract
        self.app.authorization = ('Basic', ('broker', ''))
        self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(tender_id, contract_id, owner_token), {"data": {"status": "active"}})
        # check status
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertTrue(all([i['status'] == 'complete' for i in response.json['data']['lots']]))
        self.assertEqual(response.json['data']['status'], 'complete')

    def test_2lot_3bid_1win_bug(self):
        """
        ref: http://prozorro.worksection.ua/project/141436/3931481/#com9856686
        """
        self.app.authorization = ('Basic', ('broker', ''))
        # create tender
        response = self.app.post_json('/tenders', {"data": test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']
        lots = []
        for lot in 2 * test_lots:
            # add lot
            response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender_id, owner_token), {'data': test_lots[0]})
            self.assertEqual(response.status, '201 Created')
            lots.append(response.json['data']['id'])
        self.initial_lots = lots
        # add item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [test_tender_data['items'][0] for i in lots]}})
        # add relatedLot for item
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"items": [{'relatedLot': i} for i in lots]}})
        self.assertEqual(response.status, '200 OK')
        # create bid
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id), {'data': {'selfEligible': True, 'selfQualified': True,
                                                                                      'tenderers': test_bids[0]['tenderers'], 'lotValues': [
            {"value": {"amount": 401}, 'relatedLot': lot_id}
            for lot_id in lots
        ]}})
        # create second bid
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id), {'data': {'selfEligible': True, 'selfQualified': True,
                                                                                      'tenderers': test_bids[1]['tenderers'], 'lotValues': [
            {"value": {"amount": 402}, 'relatedLot': lot_id}
            for lot_id in lots
        ]}})
        # create third bid
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.post_json('/tenders/{}/bids'.format(tender_id), {'data': {'selfEligible': True, 'selfQualified': True,
                                                                                      'tenderers': test_bids[1]['tenderers'], 'lotValues': [
            {"value": {"amount": 403}, 'relatedLot': lot_id}
            for lot_id in lots
        ]}})
        bid_id = response.json['data']['id']
        # switch to active.pre-qualification
        self.time_shift('active.pre-qualification')
        self.check_chronograph()
        response = self.app.get('/tenders/{}/qualifications?acc_token={}'.format(self.tender_id, owner_token))
        self.assertEqual(response.content_type, 'application/json')
        qualifications = response.json['data']
        self.assertEqual(len(qualifications), 6)

        for qualification in qualifications:
            if lots[1] == qualification['lotID'] and bid_id == qualification['bidID']:
                response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualification['id'], owner_token),
                                        {"data": {'status': 'unsuccessful'}})
            else:
                response = self.app.patch_json('/tenders/{}/qualifications/{}?acc_token={}'.format(self.tender_id, qualification['id'], owner_token),
                                        {"data": {'status': 'active', "qualified": True, "eligible": True}})
            self.assertEqual(response.status, '200 OK')
            if lots[1] == qualification['lotID'] and bid_id == qualification['bidID']:
                self.assertEqual(response.json['data']['status'], 'unsuccessful')
            else:
                self.assertEqual(response.json['data']['status'], 'active')
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token),
                                       {"data": {"status": "active.pre-qualification.stand-still"}})
        self.assertEqual(response.status, "200 OK")
        # switch to active.auction
        self.time_shift('active.auction')
        self.check_chronograph()
        # get auction info
        self.app.authorization = ('Basic', ('auction', ''))
        response = self.app.get('/tenders/{}/auction'.format(tender_id))
        auction_bids_data = response.json['data']['bids']
        for lot_id in lots:
            # posting auction urls
            response = self.app.patch_json('/tenders/{}/auction/{}'.format(tender_id, lot_id), {
                'data': {
                    'lots': [
                        {
                            'id': i['id'],
                            'auctionUrl': 'https://tender.auction.url'
                        }
                        for i in response.json['data']['lots']
                    ],
                    'bids': [
                        {
                            'id': i['id'],
                            'lotValues': [
                                {
                                    'relatedLot': j['relatedLot'],
                                    'participationUrl': 'https://tender.auction.url/for_bid/{}'.format(i['id'])
                                }
                                for j in i['lotValues']
                            ],
                        }
                        for i in auction_bids_data
                    ]
                }
            })
            # posting auction results
            self.app.authorization = ('Basic', ('auction', ''))
            response = self.app.post_json('/tenders/{}/auction/{}'.format(tender_id, lot_id), {'data': {'bids': auction_bids_data}})
        # for first lot
        lot_id = lots[0]
        # get awards
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending' and i['lotID'] == lot_id][0]
        # set award as active
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"status": "active", "qualified": True, "eligible": True}})
        # get contract id
        response = self.app.get('/tenders/{}'.format(tender_id))
        contract_id = response.json['data']['contracts'][-1]['id']
        # after stand slill period
        self.set_status('complete', {'status': 'active.awarded'})
        # time travel
        tender = self.db.get(tender_id)
        for i in tender.get('awards', []):
            i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)
        # sign contract
        self.app.authorization = ('Basic', ('broker', ''))
        self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(tender_id, contract_id, owner_token), {"data": {"status": "active"}})
        # for second lot
        lot_id = lots[1]
        # get awards
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending' and i['lotID'] == lot_id][0]
        # set award as unsuccessful
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"status": "unsuccessful"}})
        # get awards
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending' and i['lotID'] == lot_id][0]
        # set award as unsuccessful
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"status": "unsuccessful"}})
        # get awards
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        # get pending award
        self.assertEqual([i['id'] for i in response.json['data'] if i['status'] == 'pending' and i['lotID'] == lot_id], [])
        # after stand slill period
        self.set_status('complete', {'status': 'active.awarded'})
        # time travel
        tender = self.db.get(tender_id)
        for i in tender.get('awards', []):
            i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)
        # ping by chronograph
        self.check_chronograph()
        # check status
        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(set([i['status'] for i in response.json['data']['lots']]), set(['complete', 'unsuccessful']))
        self.assertEqual(response.json['data']['status'], 'complete')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderLotResourceTest))
    suite.addTest(unittest.makeSuite(TenderLotBidderResourceTest))
    suite.addTest(unittest.makeSuite(TenderLotFeatureBidderResourceTest))
    suite.addTest(unittest.makeSuite(TenderLotProcessTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
