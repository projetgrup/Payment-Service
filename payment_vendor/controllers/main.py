# -*- coding: utf-8 -*-
from odoo import _
from odoo.http import route, request
from odoo.exceptions import UserError
from odoo.addons.portal.controllers import portal
from odoo.addons.payment_jetcheckout_system.controllers.main import PayloxSystemController as Controller


class CustomerPortal(portal.CustomerPortal):
    @route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kwargs):
        system = kwargs.get('system', request.env.company.system)
        if system == 'vendor':
            return request.redirect('/my/payment')
        return super().home(**kwargs)


class PayloxSystemVendorController(Controller):

    def _get_tx_values(self, **kwargs):
        res = super()._get_tx_values(**kwargs)
        system = kwargs.get('system', request.env.company.system)
        if system == 'vendor':
            items = kwargs.get('items', [])
            ids = [i for i, null in items]
            item = {
                item.id: {
                    'ref': item.ref,
                    'date': item.date,
                    'desc': item.description,
                    'advance': item.advance,
                } for item in request.env['payment.item'].sudo().browse(ids)
            }
            res['paylox_transaction_item_ids'] = [(0, 0, {
                'item_id': id,
                'amount': amount,
                'ref': item[id]['ref'],
                'date': item[id]['date'],
                'desc': item[id]['desc'],
                'advance': item[id]['advance'],
            }) for id, amount in items]
        return res

    def _prepare_system(self, company, system, partner, transaction, options={}):
        options['no_compute_payment_tags'] = True
        res = super()._prepare_system(company, system, partner, transaction, options=options)
        if system == 'vendor':
            try:
                wizard = request.env['syncops.sync.wizard'].sudo().create({
                    'type': 'item',
                    'system': 'vendor',
                    'type_item_subtype': company.syncops_sync_item_subtype,
                })
                wizard.with_context(partner=partner).confirm()
                wizard.with_context(wizard_id=wizard.id, partner=partner).sync()
            except:
                pass

        campaign = res['campaign']
        payments, payment_tags = partner._get_payments()
        currency = payments.mapped('currency_id')
        if len(currency) > 1:
            raise UserError(_('Payment items must share one common currency'))
        if payment_tags and payment_tags[0].campaign_id:
            campaign = payment_tags[0].campaign_id.name

        res.update({
            'currency': currency,
            'campaign': campaign,
            'payments': payments,
            'payment_tags': payment_tags,
        })
        return res
