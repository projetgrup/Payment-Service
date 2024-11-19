# -*- coding: utf-8 -*-
import json
import base64
from werkzeug.exceptions import NotFound

from odoo import _
from odoo.http import route, request, Response
from odoo.addons.portal.controllers import portal
from odoo.addons.payment_jetcheckout_system.controllers.main import PayloxSystemController as Controller


#class CustomerPortal(portal.CustomerPortal):
#    @route(['/my', '/my/home'], type='http', auth='user', website=True)
#    def home(self, **kwargs):
#        system = kwargs.get('system', request.env.company.system)
#        if system == 'jewelry':
#            return request.redirect('/my/payment')
#        return super().home(**kwargs)


class PayloxSystemJewelryController(Controller):

#    @route(['/my/jewelry'], type='http', auth='user', website=True)
#    def page_jewelry(self, **kwargs):
#        system = kwargs.get('system', request.env.company.system)
#        if system == 'jewelry':
#            return request.redirect('/my/payment')
#        return super().home(**kwargs)
#
#    def _get_tx_values(self, **kwargs):
#        res = super()._get_tx_values(**kwargs)
#        system = kwargs.get('system', request.env.company.system)
#        if system == 'jewelry':
#            pass
#        return res

    def _prepare_system(self, company, system, partner, transaction, options={}):
        res = super()._prepare_system(company, system, partner, transaction, options=options)
        if system == 'jewelry':
            result = request.env['syncops.connector'].sudo()._execute('payment_get_partner_balance', params={'ref': partner.ref})
            balances = result if result and len(result) > 1 else [{'name': 'TRY', 'balance': 0.0}]
            res.update({
                'balances': balances,
                'currency': company.currency_id,
                'options': {
                    'listen_price_active': True,
                    'save_order_active': True
                },
            })
        return res

    @route(['/my/jewelry/register'], type='http', auth='public', website=True)
    def page_jewelry_register(self, **kwargs):
        system = request.env.company.system
        if system == 'jewelry':
            values = {
                'company': request.env.company,
            }
            return request.render('payment_jewelry.page_regsiter', values)
        raise NotFound()

    @route('/my/jewelry/register/query', type='json', auth='public', website=True)
    def page_jewelry_register_query(self, vat):
        result = request.env['syncops.connector'].sudo()._execute('partner_get_company', params={'vat': vat})
        if result is None:
            return {'error': _('An error occured. Please contact with system administrator.')}
        return result[0]

    @route('/my/jewelry/webhook', type='json', auth='public', methods=['POST'], sitemap=False, csrf=False, website=True)
    def webhook_jewelry(self, **kwargs):
        params = json.loads(request.httprequest.data)
        headers = request.httprequest.headers
        if 'Authorization' not in headers:
            return Response('Access Denied', status=401)

        code = headers.get('Authorization').split(' ', 1)[1]
        auth = base64.b64decode(code).decode('utf-8')
        username, password = auth.split(':', 1)
        token = request.env['syncops.connector'].sudo().search([('username', '=', username), ('token', '=', password)], limit=1)
        if not token:
            return Response('Access Denied', status=401)

        response = {}
        products = request.env['product.template'].sudo().with_context(system='jewelry')
        domain = [('system', '=', 'jewelry'), ('company_id', '=', request.env.company.id)]
        if 'XAUTRY' in params:
            response['XAUTRY'] = params['XAUTRY']
            products.search(domain+[('default_code', '=', 'XAUTRY')], limit=1).write({'list_price': params['XAUTRY']})
        if 'XAGTRY' in params:
            response['XAGTRY'] = params['XAGTRY']
            products.search(domain+[('default_code', '=', 'XAGTRY')], limit=1).write({'list_price': params['XAGTRY']})
        return response

    @route('/my/product', type='http', auth='public', methods=['GET', 'POST'], sitemap=False, csrf=False, website=True)
    def page_product(self, **kwargs):
        system = request.env.company.system
        if system == 'jewelry':
            raise NotFound()
        return super().page_product(**kwargs)
