# -*- coding: utf-8 -*-
import re
import werkzeug

from odoo import _
from odoo.http import route, request
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round
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

    def _get_data_values(self, data, transaction, **kwargs):
        values = super()._get_data_values(data, transaction, **kwargs)
        if request.env.company.system == 'supplier':
            ref = request.httprequest.referrer
            if ref and '/payment/token/verify' in ref:
                partner = self._get_partner(kwargs['partner'], parent=True)
                reference = partner.bank_ids and partner.bank_ids[0]['api_ref']
                if not reference:
                    raise ValidationError(_('%s must have at least one bank account which is verified.' % partner.name))

                if transaction.company_id.payment_page_token_wo_commission:
                    amount = float_round(transaction.amount * (1 - (transaction.jetcheckout_commission_rate / 100)), 4)
                else:
                    amount = float(kwargs['amount'])

                values.update({
                    'is_submerchant_payment': True,
                    'submerchant_external_id': reference,
                    'submerchant_price': amount,
                })
                if not kwargs.get('verify'):
                    values.update({
                        'is_3d': False,
                    })
        return values
