# -*- coding: utf-8 -*-
import re
import werkzeug

from odoo import _
from odoo.http import route, request
from odoo.exceptions import ValidationError
from odoo.addons.portal.controllers import portal
from odoo.addons.payment_jetcheckout_system.controllers.main import PayloxSystemController as Controller


class CustomerPortal(portal.CustomerPortal):

    @route(['/my', '/my/home'], type='http', auth='user', website=True, sitemap=False)
    def home(self, **kwargs):
        system = kwargs.get('system', request.env.company.system)
        if system == 'supplier':
            return request.redirect('/my/payment')
        return super().home(**kwargs)


class PayloxSystemSupplierController(Controller):

    def _get_data_values(self, data, **kwargs):
        values = super()._get_data_values(data, **kwargs)
        if request.env.company.system == 'supplier':
            partner = self._get_partner(kwargs['partner'], parent=True)
            reference = partner.bank_ids and partner.bank_ids[0]['api_ref']
            if not reference:
                raise ValidationError(_('%s must have at least one bank account which is verified.' % partner.name))
            values.update({
                'is_submerchant_payment': True,
                'submerchant_external_id': reference,
                'submerchant_price': data['amount']/100,
            })
            if not kwargs.get('verify'):
                values.update({
                    'is_3d': False,
                })
        return values

    @route(['/payment/token/verify'], type='http', auth='user', website=True, sitemap=False)
    def payment_token_verify(self, **kwargs):
        acquirer = self._get_acquirer()
        company = request.env.company
        currency = company.currency_id

        user = not request.env.user.share
        partner = company.partner_id
        partner_commercial = partner
        partner_contact = False

        language = request.env['res.lang']._lang_get(request.env.lang)
        campaign = self._get_campaign(partner=partner)

        values = {
            'user': user,
            'contact': partner_contact,
            'partner': partner_commercial,
            'company': company,
            'acquirer': acquirer,
            'campaign': campaign,
            'language': language,
            'currency': currency,
            'success_url': '/payment/token/success',
            'fail_url': '/payment/token/fail',
        }
        return request.render('payment_jetcheckout.page_token_verify', values)

    @route(['/payment/token/success', '/payment/token/fail'], type='http', auth='public', methods=['POST'], sitemap=False, csrf=False, save_session=False)
    def payment_token_finalize(self, **kwargs):
        url, tx, status = self._process(**kwargs)
        url = '/payment/token/result'
        if tx.jetcheckout_order_id:
            url += '?=%s' % tx.jetcheckout_order_id
        return werkzeug.utils.redirect(url)

    @route(['/payment/token/result'], type='http', auth='public', methods=['GET'], website=True, csrf=False, sitemap=False)
    def payment_token_result(self, **kwargs):
        values = {}
        if '' in kwargs:
            txid = re.split(r'\?|%3F', kwargs[''])[0]
            values['tx'] = request.env['payment.transaction'].sudo().search([('jetcheckout_order_id', '=', txid)], limit=1)
        else:
            txid = self._get('tx', 0)
            values['tx'] = request.env['payment.transaction'].sudo().browse(txid)
        self._del()
        return request.render('payment_supplier.page_token_result', values)
