# -*- coding: utf-8 -*-
import re
import uuid
import werkzeug

from datetime import date
from urllib.parse import urlparse
from odoo.http import request, route
from odoo.addons.payment_jetcheckout_system.controllers.main import PayloxSystemController as Controller


class PayloxAgreementController(Controller):

    def _get_agreement_path(self):
        if request.httprequest.method == 'POST':
            address = urlparse(request.httprequest.referrer).path
        else:
            address = urlparse(request.httprequest.url).path
        return re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-[0-9a-f]+', '', address)

    def _prepare_agreements(self, agreement_ids):
        path = self._get_agreement_path()
        page = request.env['payment.page'].sudo().search([('path', 'like', '%s%%' % path)], limit=1)
        return [(0, 0, {
            'uuid': str(uuid.uuid4()),
            'page_id': page.id,
            'agreement_id': agreement_id,
        }) for agreement_id in agreement_ids]

    def _get_agreements(self, agreement_id=False, product_id=False):
        if not request.env.company.system_agreement:
            return []

        path = self._get_agreement_path()
        domain = [
            ('active', '=', True),
            ('page_ids.path', 'like', '%s%%' % path),
            ('company_id', '=', request.env.company.id),
        ]
        if agreement_id:
            domain += [('id', '=', agreement_id)]
        else:
            if product_id:
                domain += [('product_ids', 'in', [product_id])]
            else:
                domain += [('product_ids', '=', False)]

            today = date.today()
            domain += [
                '|', ('date_start', '=', False), ('date_start', '<=', today),
                '|', ('date_end', '=', False), ('date_end', '>=', today),
            ]
        return request.env['payment.agreement'].sudo().search(domain)

    def _get_tx_values(self, **kwargs):
        vals = super()._get_tx_values(**kwargs)
        agreements = kwargs.get('agreements', [])
        if agreements:
            vals.update({'paylox_agreement_ids': self._prepare_agreements(agreements)})
        return vals

    def _prepare(self, **kwargs):
        res = super()._prepare(**kwargs)
        res['agreements'] = self._get_agreements()
        return res

    def _prepare_system(self, *args, **kwargs):
        res = super()._prepare_system(*args, **kwargs)
        res['agreements'] = self._get_agreements()
        return res

    @route(['/my/agreement'], type='json', auth='public', website=True, csrf=False)
    def page_system_agreement(self, agreement_id=None, partner_id=None, product_id=None, currency_id=None, amount=None):
        agreement = self._get_agreements(agreement_id, product_id)
        if not agreement:
            return False

        if product_id:
            return [{'id': a.id, 'text': a.text} for a in agreement]

        partner = request.env['res.partner'].sudo().browse(partner_id)
        currency = request.env['res.currency'].sudo().browse(currency_id)
        return {
            'id': agreement.id,
            'name': agreement.name,
            'body': agreement.render({
                'partner': partner,
                'amount': amount,
                'currency': currency,
            })
        }

    @route(['/my/agreement/<uuid>'], type='http', methods=['GET'], auth='public', website=True, csrf=False)
    def page_system_transaction_agreement(self, uuid):
        agreement = request.env['payment.transaction.agreement'].sudo().search([('uuid', '=', uuid)], limit=1)
        if not agreement:
            raise werkzeug.exceptions.NotFound()

        return agreement.body
