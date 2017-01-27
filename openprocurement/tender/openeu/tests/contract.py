# -*- coding: utf-8 -*-
import unittest
from copy import deepcopy
from datetime import timedelta

from openprocurement.api.models import get_now
from openprocurement.api.tests.base import test_organization, create_classmethod
from openprocurement.tender.openeu.tests.base import (
    BaseTenderContentWebTest,
    test_tender_data,
    test_features_tender_data,
    test_bids
)
from openprocurement.api.tests.contract_test_utils import (
    create_tender_contract_invalid,
    get_tender_contract,
    get_tender_contracts,
    not_found,
    create_tender_contract_document,
    put_tender_contract_document,
    patch_tender_contract_document
)
from openprocurement.tender.openeu.tests.contract_test_utils import (
    contract_termination,
    create_tender_contract,
    patch_tender_contract_datesigned,
    patch_tender_contract
)



class TenderContractResourceTest(BaseTenderContentWebTest):
    #initial_data = tender_data
    initial_status = 'active.qualification'
    initial_bids = test_bids

    initial_auth = ('Basic', ('broker', ''))
    test_create_tender_contract_invalid = create_classmethod(create_tender_contract_invalid)
    test_get_tender_contract = create_classmethod(get_tender_contract)
    test_get_tender_contracts = create_classmethod(get_tender_contracts)
    test_contract_termination = create_classmethod(contract_termination)
    test_create_tender_contract = create_classmethod(create_tender_contract)
    test_patch_tender_contract_datesigned = create_classmethod(patch_tender_contract_datesigned)
    test_patch_tender_contract = create_classmethod(patch_tender_contract)
    def setUp(self):
        super(TenderContractResourceTest, self).setUp()
        # Create award
        self.supplier_info = deepcopy(test_organization)
        self.app.authorization = ('Basic', ('token', ''))
        response = self.app.post_json('/tenders/{}/awards'.format(
            self.tender_id), {'data': {'suppliers': [self.supplier_info], 'status': 'pending', 'bid_id': self.initial_bids[0]['id'], 'value': {"amount": 500, "currency": "UAH", "valueAddedTaxIncluded": True}, 'items': test_tender_data["items"]}})
        award = response.json['data']
        self.award_id = award['id']
        self.app.authotization = ('Basic', ('broker', ''))
        response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, self.award_id), {"data": {"status": "active", "qualified": True, "eligible": True}})


class TenderContractDocumentResourceTest(BaseTenderContentWebTest):
    #initial_data = tender_data
    initial_status = 'active.qualification'
    status = "unsuccessful"
    initial_bids = test_bids

    initial_auth = ('Basic', ('broker', ''))

    test_not_found = create_classmethod(not_found)
    test_create_tender_contract_document = create_classmethod(create_tender_contract_document)
    test_put_tender_contract_document = create_classmethod(put_tender_contract_document)
    test_patch_tender_contract_document = create_classmethod(patch_tender_contract_document)

    def setUp(self):
        super(TenderContractDocumentResourceTest, self).setUp()
        # Create award
        supplier_info = deepcopy(test_organization)
        self.app.authorization = ('Basic', ('token', ''))
        response = self.app.post_json('/tenders/{}/awards'.format(
            self.tender_id), {'data': {'suppliers': [supplier_info], 'status': 'pending', 'bid_id': self.initial_bids[0]['id']}})
        award = response.json['data']
        self.award_id = award['id']
        response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, self.award_id), {"data": {"status": "active", "qualified": True, "eligible": True}})
        # Create contract for award
        response = self.app.post_json('/tenders/{}/contracts'.format(self.tender_id), {'data': {'title': 'contract title', 'description': 'contract description', 'awardID': self.award_id}})
        contract = response.json['data']
        self.contract_id = contract['id']
        self.app.authorization = ('Basic', ('broker', ''))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderContractResourceTest))
    suite.addTest(unittest.makeSuite(TenderContractDocumentResourceTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
