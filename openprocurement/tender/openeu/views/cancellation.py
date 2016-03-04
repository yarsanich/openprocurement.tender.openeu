# -*- coding: utf-8 -*-
from openprocurement.api.utils import opresource
from openprocurement.api.views.cancellation import TenderCancellationResource as BaseResource
from openprocurement.tender.openeu.utils import add_next_award


@opresource(name='TenderEU Cancellations',
            collection_path='/tenders/{tender_id}/cancellations',
            path='/tenders/{tender_id}/cancellations/{cancellation_id}',
            procurementMethodType='aboveThresholdEU',
            description="Tender cancellations")
class TenderCancellationResource(BaseResource):
    """ TenderEU Cancellations """

    def cancel_tender(self):
        tender = self.request.validated['tender']
        if tender.status in ['active.tendering']:
            tender.bids = []
        if tender.status in ['active.pre-qualification', 'active.pre-qualification.stand-still', 'active.auction']:
            [setattr(i, 'status', 'invalid') for i in tender.bids]
        tender.status = 'cancelled'

    def cancel_lot(self, cancellation=None):
        if not cancellation:
            cancellation = self.context
        tender = self.request.validated['tender']
        [setattr(i, 'status', 'cancelled') for i in tender.lots if i.id == cancellation.relatedLot]
        cancelled_lots = [i.id for i in tender.lots if i.status == 'cancelled']
        cancelled_items = [i.id for i in tender.items if i.relatedLot in cancelled_lots]
        cancelled_features = [
            i.code
            for i in (tender.features or [])
            if i.featureOf == 'lot' and i.relatedItem in cancelled_lots or i.featureOf == 'item' and i.relatedItem in cancelled_items
        ]
        if tender.status in ['active.tendering', 'active.pre-qualification', 'active.pre-qualification.stand-still', 'active.auction']:
            for bid in tender.bids:
                if tender.status == "active.tendering":
                    bid.documents = [i for i in bid.documents if i.documentOf != 'lot' or i.relatedItem not in cancelled_lots]
                bid.financialDocuments = [i for i in bid.financialDocuments if i.documentOf != 'lot' or i.relatedItem not in cancelled_lots]
                bid.eligibilityDocuments = [i for i in bid.eligibilityDocuments if i.documentOf != 'lot' or i.relatedItem not in cancelled_lots]
                bid.qualificationDocuments = [i for i in bid.qualificationDocuments if i.documentOf != 'lot' or i.relatedItem not in cancelled_lots]
                bid.parameters = [i for i in bid.parameters if i.code not in cancelled_features]
                bid.lotValues = [i for i in bid.lotValues if i.relatedLot not in cancelled_lots]
                if not bid.lotValues:
                    bid.status = 'invalid'
        for qualification in tender.qualifications:
            if qualification.lotID in cancelled_lots:
                qualification.status = 'cancelled'
        statuses = set([lot.status for lot in tender.lots])
        if statuses == set(['cancelled']):
            self.cancel_tender()
        elif not statuses.difference(set(['unsuccessful', 'cancelled'])):
            tender.status = 'unsuccessful'
        elif not statuses.difference(set(['complete', 'unsuccessful', 'cancelled'])):
            tender.status = 'complete'
        if tender.status == 'active.auction' and all([
            i.auctionPeriod and i.auctionPeriod.endDate
            for i in self.request.validated['tender'].lots
            if i.status == 'active'
        ]):
            add_next_award(self.request)
