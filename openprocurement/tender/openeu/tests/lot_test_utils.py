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
from openprocurement.tender.openeu.tests.base import (BaseTenderContentWebTest,
                                                      BaseTenderWebTest,
                                                      test_tender_data,
                                                      test_lots,
                                                      test_bids)

def create_tender_lot(self):
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token), {'data': test_lots[0]})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    lot = response.json['data']
    self.assertEqual(lot['title'], 'lot title')
    self.assertEqual(lot['description'], 'lot description')
    self.assertIn('id', lot)
    self.assertIn(lot['id'], response.headers['Location'])
    self.assertNotIn('guarantee', lot)

    lot2 = deepcopy(test_lots[0])
    lot2['guarantee'] = {"amount": 100500, "currency": "USD"}
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token), {'data': lot2})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    data = response.json['data']
    self.assertIn('guarantee', data)
    self.assertEqual(data['guarantee']['amount'], 100500)
    self.assertEqual(data['guarantee']['currency'], "USD")

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertIn('guarantee', response.json['data'])
    self.assertEqual(response.json['data']['guarantee']['amount'], 100500)
    self.assertEqual(response.json['data']['guarantee']['currency'], "USD")
    self.assertNotIn('guarantee', response.json['data']['lots'][0])

    lot3 = deepcopy(test_lots[0])
    lot3['guarantee'] = {"amount": 500, "currency": "UAH"}
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token), {'data': lot3}, status=422)
    self.assertEqual(response.status, '422 Unprocessable Entity')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': [u'lot guarantee currency should be identical to tender guarantee currency'], u'location': u'body', u'name': u'lots'}
    ])

    lot3['guarantee'] = {"amount": 500}
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token), {'data': lot3}, status=422)
    self.assertEqual(response.status, '422 Unprocessable Entity')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': [u'lot guarantee currency should be identical to tender guarantee currency'], u'location': u'body', u'name': u'lots'}
    ])

    lot3['guarantee'] = {"amount": 20, "currency": "USD"}
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token), {'data': lot3})
    self.assertEqual(response.status, '201 Created')
    data = response.json['data']
    self.assertIn('guarantee', data)
    self.assertEqual(data['guarantee']['amount'], 20)
    self.assertEqual(data['guarantee']['currency'], "USD")

    response = self.app.get('/tenders/{}'.format(self.tender_id))
    self.assertIn('guarantee', response.json['data'])
    self.assertEqual(response.json['data']['guarantee']['amount'], 100500 + 20)
    self.assertEqual(response.json['data']['guarantee']['currency'], "USD")

    response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token), {"data": {"guarantee": {"currency": "EUR"}}})
    self.assertEqual(response.json['data']['guarantee']['amount'], 100500 + 20)
    self.assertEqual(response.json['data']['guarantee']['currency'], "EUR")
    self.assertNotIn('guarantee', response.json['data']['lots'][0])
    self.assertEqual(response.json['data']['lots'][1]['guarantee']['amount'], 100500)
    self.assertEqual(response.json['data']['lots'][1]['guarantee']['currency'], "EUR")
    self.assertEqual(response.json['data']['lots'][2]['guarantee']['amount'], 20)
    self.assertEqual(response.json['data']['lots'][2]['guarantee']['currency'], "EUR")
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token), {'data': lot}, status=422)
    self.assertEqual(response.status, '422 Unprocessable Entity')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': [u'Lot id should be uniq for all lots'], u'location': u'body', u'name': u'lots'}
    ])

def patch_tender_lot(self):
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': test_lots[0]})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    lot = response.json['data']

    response = self.app.patch_json('/tenders/{}/lots/{}?acc_token={}'.format(self.tender_id, lot['id'], self.tender_token),
                                   {"data": {"title": "new title"}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["title"], "new title")

    response = self.app.patch_json('/tenders/{}/lots/{}?acc_token={}'.format(self.tender_id, lot['id'], self.tender_token), {"data": {"guarantee": {"amount": 12}}})
    self.assertEqual(response.status, '200 OK')
    self.assertIn('guarantee', response.json['data'])
    self.assertEqual(response.json['data']['guarantee']['amount'], 12)
    self.assertEqual(response.json['data']['guarantee']['currency'], 'UAH')

    response = self.app.patch_json('/tenders/{}/lots/{}?acc_token={}'.format(self.tender_id, lot['id'], self.tender_token), {"data": {"guarantee": {"currency": "USD"}}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.json['data']['guarantee']['currency'], 'UAH')

    response = self.app.patch_json('/tenders/{}/lots/some_id'.format(self.tender_id), {"data": {"title": "other title"}}, status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'lot_id'}
    ])

    response = self.app.patch_json('/tenders/some_id/lots/some_id', {"data": {"title": "other title"}}, status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'tender_id'}
    ])

    response = self.app.get('/tenders/{}/lots/{}'.format(self.tender_id, lot['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["title"], "new title")

    self.time_shift('active.pre-qualification')
    self.check_chronograph()

    response = self.app.patch_json('/tenders/{}/lots/{}?acc_token={}'.format(self.tender_id, lot['id'], self.tender_token),
                                   {"data": {"title": "other title"}}, status=403)

    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can't update lot in current (unsuccessful) tender status")

def delete_tender_lot(self):
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': test_lots[0]})

    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    lot = response.json['data']

    response = self.app.delete('/tenders/{}/lots/{}?acc_token={}'.format(self.tender_id, lot['id'], self.tender_token))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data'], lot)

    response = self.app.delete('/tenders/{}/lots/some_id?acc_token={}'.format(self.tender_id, self.tender_token), status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'lot_id'}
    ])

    response = self.app.delete('/tenders/some_id/lots/some_id', status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
            u'url', u'name': u'tender_id'}
    ])

    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
                                  {'data': test_lots[0]})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    lot = response.json['data']

    response = self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token), {"data": {
        "items": [
            {
                'relatedLot': lot['id']
            }
        ]
    }})
    self.assertEqual(response.status, '200 OK')

    response = self.app.delete('/tenders/{}/lots/{}?acc_token={}'.format(self.tender_id, lot['id'], self.tender_token), status=422)
    self.assertEqual(response.status, '422 Unprocessable Entity')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': [{u'relatedLot': [u'relatedLot should be one of lots']}], u'location': u'body', u'name': u'items'}
    ])
    self.time_shift('active.pre-qualification')
    self.check_chronograph()

    response = self.app.delete('/tenders/{}/lots/{}?acc_token={}'.format(self.tender_id, lot['id'], self.tender_token), status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can't delete lot in current (unsuccessful) tender status")

def tender_lot_guarantee(self):
    data = deepcopy(test_tender_data)
    data['guarantee'] = {"amount": 100, "currency": "USD"}
    response = self.app.post_json('/tenders', {'data': data})
    tender = response.json['data']
    owner_token = response.json['access']['token']
    self.assertEqual(response.status, '201 Created')
    self.assertIn('guarantee', response.json['data'])
    self.assertEqual(response.json['data']['guarantee']['amount'], 100)
    self.assertEqual(response.json['data']['guarantee']['currency'], "USD")

    lot = deepcopy(test_lots[0])
    lot['guarantee'] = {"amount": 20, "currency": "USD"}
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender['id'], owner_token), {'data': lot})
    self.assertEqual(response.status, '201 Created')
    self.assertIn('guarantee', response.json['data'])
    self.assertEqual(response.json['data']['guarantee']['amount'], 20)
    self.assertEqual(response.json['data']['guarantee']['currency'], "USD")

    response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {'data': {'guarantee': {"currency": "GBP"}}})
    self.assertEqual(response.status, '200 OK')
    self.assertIn('guarantee', response.json['data'])
    self.assertEqual(response.json['data']['guarantee']['amount'], 20)
    self.assertEqual(response.json['data']['guarantee']['currency'], "GBP")

    lot['guarantee'] = {"amount": 20, "currency": "GBP"}
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender['id'], owner_token), {'data': lot})
    self.assertEqual(response.status, '201 Created')
    lot_id = response.json['data']['id']
    self.assertEqual(response.json['data']['guarantee']['amount'], 20)
    self.assertEqual(response.json['data']['guarantee']['currency'], "GBP")

    response = self.app.get('/tenders/{}'.format(tender['id']))
    self.assertEqual(response.json['data']['guarantee']['amount'], 20 + 20)
    self.assertEqual(response.json['data']['guarantee']['currency'], "GBP")

    lot2 = deepcopy(test_lots[0])
    lot2['guarantee'] = {"amount": 30, "currency": "GBP"}
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender['id'], owner_token), {'data': lot2})
    self.assertEqual(response.status, '201 Created')
    lot2_id = response.json['data']['id']
    self.assertEqual(response.json['data']['guarantee']['amount'], 30)
    self.assertEqual(response.json['data']['guarantee']['currency'], "GBP")

    lot2['guarantee'] = {"amount": 40, "currency": "USD"}
    response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(tender['id'], owner_token), {'data': lot2}, status=422)
    self.assertEqual(response.status, '422 Unprocessable Entity')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': [u'lot guarantee currency should be identical to tender guarantee currency'], u'location': u'body', u'name': u'lots'}
    ])

    response = self.app.get('/tenders/{}'.format(tender['id']))
    self.assertIn('guarantee', response.json['data'])
    self.assertEqual(response.json['data']['guarantee']['amount'], 20 + 20 + 30)
    self.assertEqual(response.json['data']['guarantee']['currency'], "GBP")

    response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {"data": {"guarantee": {"amount": 55}}})
    self.assertEqual(response.json['data']['guarantee']['amount'], 20 + 20 + 30)
    self.assertEqual(response.json['data']['guarantee']['currency'], "GBP")

    response = self.app.patch_json('/tenders/{}/lots/{}?acc_token={}'.format(tender['id'], lot2_id, owner_token), {'data': {'guarantee': {"amount": 35, "currency": "GBP"}}})
    self.assertEqual(response.json['data']['guarantee']['amount'], 35)
    self.assertEqual(response.json['data']['guarantee']['currency'], "GBP")

    response = self.app.get('/tenders/{}'.format(tender['id']))
    self.assertIn('guarantee', response.json['data'])
    self.assertEqual(response.json['data']['guarantee']['amount'], 20 + 20 + 35)
    self.assertEqual(response.json['data']['guarantee']['currency'], "GBP")

    for l_id in (lot_id, lot2_id):
        response = self.app.patch_json('/tenders/{}/lots/{}?acc_token={}'.format(tender['id'], l_id, owner_token), {'data': {'guarantee': {"amount": 0, "currency": "GBP"}}})
        self.assertEqual(response.json['data']['guarantee']['amount'], 0)
        self.assertEqual(response.json['data']['guarantee']['currency'], "GBP")

    response = self.app.get('/tenders/{}'.format(tender['id']))
    self.assertIn('guarantee', response.json['data'])
    self.assertEqual(response.json['data']['guarantee']['amount'], 20)
    self.assertEqual(response.json['data']['guarantee']['currency'], "GBP")

    for l_id in (lot_id, lot2_id):
        response = self.app.delete('/tenders/{}/lots/{}?acc_token={}'.format(tender['id'], l_id, owner_token))
        self.assertEqual(response.status, '200 OK')

    response = self.app.get('/tenders/{}'.format(tender['id']))
    self.assertIn('guarantee', response.json['data'])
    self.assertEqual(response.json['data']['guarantee']['amount'], 20)
    self.assertEqual(response.json['data']['guarantee']['currency'], "GBP")
