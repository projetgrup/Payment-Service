# -*- coding: utf-8 -*-
import json
import base64
import hashlib
import logging
import requests
from urllib.parse import quote

from odoo.http import Response
from odoo.tools.translate import _, _lt
from odoo.exceptions import ValidationError
from odoo.addons.base_rest import restapi
from odoo.addons.base_rest.controllers.main import RestController
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)

RESPONSE = {
    200: {"status": 0, "message": "Success"}
}


class PaymentAPIController(RestController):
    _root_path = "/api/v1/"
    _collection_name = "payment"
    _default_auth = "public"


class PaymentAPIService(Component):
    _inherit = "base.rest.service"
    _name = "payment"
    _usage = "payment"
    _collection = "payment"
    _description = _lt("""
        <br/>
        <h1 class="dCEJze">Description</h1>
        <p>This API helps you create payments and query their statuses with a special key which is privately generated for you.</p>
        <p>Firstly, use "Prepare Payment" method to initialize a payment request. Then, if everything goes well, server will send you a hash string.</p>
        <p>Now, you can navigate to <code>/payment/card?=&lt;hash&gt;</code> address to get payment form.</p>
        <p>When payment is done, its result will send to the address which you have specified when initializing the payment.</p>
        <p>Afterwards, you can use "Payment Operation" methods for cancelling, refunding, expiring or deleting the payment.</p>
    """)

    @restapi.method(
        [(["/installments"], "GET")],
        input_param=Datamodel("payment.installment.input"),
        output_param=Datamodel("payment.installment.output"),
        auth="public",
        tags=[_lt("Payment Initialization")]
    )
    def payment_installments(self, params):
        try:
            company = self.env.company.id

            api = self._get_api(company, params.apikey)
            if not api:
                return Response("Application key is not matched", status=401, mimetype="application/json")

            installments = self._get_installments(api, params)

            ResponseOk = self.env.datamodels["payment.installment.output"]
            return ResponseOk(**installments, **RESPONSE[200])
        except Exception as e:
            _logger.error(e)
            return Response("Server Error", status=500, mimetype="application/json")
    payment_installments.__doc__ = _lt("Get Installments")

    @restapi.method(
        [(["/prepare"], "POST")],
        input_param=Datamodel("payment.prepare.input"),
        output_param=Datamodel("payment.prepare.output"),
        auth="public",
        tags=[_lt("Payment Initialization")]
    )
    def payment_prepare(self, params):
        try:
            company = self.env.company.id

            api = self._get_api(company, params.apikey)
            if not api:
                return Response("Application key is not matched", status=401, mimetype="application/json")

            hash = self._get_hash(api, params.hash, params.id)
            if not hash:
                return Response("Hash is not matched", status=401, mimetype="application/json")

            self._create_transaction(api, hash, params)

            ResponseOk = self.env.datamodels["payment.prepare.output"]
            return ResponseOk(hash=quote(hash), **RESPONSE[200])
        except Exception as e:
            _logger.error(e)
            return Response("Server Error", status=500, mimetype="application/json")
    payment_prepare.__doc__ = _lt("Prepare Payment")

    @restapi.method(
        [(["/result"], "GET")],
        input_param=Datamodel("payment.credential.hash"),
        output_param=Datamodel("payment.result.output"),
        auth="public",
        tags=[_lt("Payment Finalization")]
    )
    def payment_result(self, params):
        try:
            company = self.env.company.id

            api = self._get_api(company, params.apikey)
            if not api:
                return Response("Application key is not matched", status=401, mimetype="application/json")

            tx = self._get_transaction_from_hash(company, params.hash)
            if not tx:
                return Response("Transaction not found", status=404, mimetype="application/json")

            result = self._get_transaction_result(tx)

            ResponseOk = self.env.datamodels["payment.result.output"]
            return ResponseOk(**result, **RESPONSE[200])
        except Exception as e:
            _logger.error(e)
            return Response("Server Error", status=500, mimetype="application/json")
    payment_result.__doc__ = _lt("Payment Result")

    @restapi.webhook(
        input_param=Datamodel("payment.result.webhook"),
        auth="public",
        tags=[_lt("Payment Finalization")]
    )
    def payment_webhook(self):
        pass
    payment_webhook.__doc__ = _lt("Payment Webhook")

    @restapi.method(
        [(["/status"], "GET")],
        input_param=Datamodel("payment.credential.hash"),
        output_param=Datamodel("payment.status.output"),
        auth="public",
        tags=[_lt("Payment Finalization")]
    )
    def payment_status(self, params):
        try:
            company = self.env.company.id
            api = self._get_api(company, params.apikey)
            if not api:
                return Response("Application key is not matched", status=401, mimetype="application/json")

            tx = self._get_transaction_from_hash(company, params.hash)
            if not tx:
                return Response("Transaction not found", status=404, mimetype="application/json")
            elif not tx.jetcheckout_order_id:
                return Response("Transaction is being processed, but it has not been done yet.", status=202, mimetype="application/json")

            result = self._query_transaction(tx)

            ResponseOk = self.env.datamodels["payment.status.output"]
            return ResponseOk(**result, **RESPONSE[200])
        except Exception as e:
            _logger.error(e)
            return Response("Server Error", status=500, mimetype="application/json")
    payment_status.__doc__ = _lt("Payment Status")

    @restapi.method(
        [(["/cancel"], "PUT")],
        input_param=Datamodel("payment.credential.hash"),
        output_param=Datamodel("payment.output"),
        auth="public",
        tags=[_lt("Payment Operation")]
    )
    def payment_cancel(self, params):
        try:
            company = self.env.company.id
            api = self._get_api(company, params.apikey)
            if not api:
                return Response("Application key is not matched", status=401, mimetype="application/json")

            tx = self._get_transaction_from_hash(company, params.hash)
            if not tx:
                return Response("Transaction not found", status=404, mimetype="application/json")

            self._cancel_transaction(tx)

            ResponseOk = self.env.datamodels["payment.output"]
            return ResponseOk(**RESPONSE[200])
        except Exception as e:
            _logger.error(e)
            return Response("Server Error", status=500, mimetype="application/json")
    payment_cancel.__doc__ = _lt("Cancel Payment")

    @restapi.method(
        [(["/refund"], "PUT")],
        input_param=Datamodel("payment.refund.input"),
        output_param=Datamodel("payment.output"),
        auth="public",
        tags=[_lt("Payment Operation")]
    )
    def payment_refund(self, params):
        try:
            company = self.env.company.id
            api = self._get_api(company, params.apikey)
            if not api:
                return Response("Application key is not matched", status=401, mimetype="application/json")

            tx = self._get_transaction_from_hash(company, params.hash)
            if not tx:
                return Response("Transaction not found", status=404, mimetype="application/json")

            self._refund_transaction(tx, params.amount)

            ResponseOk = self.env.datamodels["payment.output"]
            return ResponseOk(**RESPONSE[200])
        except Exception as e:
            _logger.error(e)
            return Response("Server Error", status=500, mimetype="application/json")
    payment_refund.__doc__ = _lt("Refund Payment")

    @restapi.method(
        [(["/expire"], "PUT")],
        input_param=Datamodel("payment.credential.hash"),
        output_param=Datamodel("payment.output"),
        auth="public",
        tags=[_lt("Payment Operation")]
    )
    def payment_expire(self, params):
        try:
            company = self.env.company.id

            api = self._get_api(company, params.apikey)
            if not api:
                return Response("Application key is not matched", status=401, mimetype="application/json")

            tx = self._get_transaction_from_hash(company, params.hash)
            if not tx:
                return Response("Transaction not found", status=404, mimetype="application/json")

            self._expire_transaction(tx)

            ResponseOk = self.env.datamodels["payment.output"]
            return ResponseOk(**RESPONSE[200])
        except Exception as e:
            _logger.error(e)
            return Response("Server Error", status=500, mimetype="application/json")
    payment_expire.__doc__ = _lt("Expire Payment")

    @restapi.method(
        [(["/delete"], "DELETE")],
        input_param=Datamodel("payment.credential.hash"),
        output_param=Datamodel("payment.output"),
        auth="public",
        tags=[_lt("Payment Operation")]
    )
    def payment_delete(self, params):
        try:
            company = self.env.company.id

            api = self._get_api(company, params.apikey)
            if not api:
                return Response("Application key is not matched", status=401, mimetype="application/json")

            tx = self._get_transaction_from_hash(company, params.hash)
            if not tx:
                return Response("Transaction not found", status=404, mimetype="application/json")

            self._delete_transaction(tx)
            return Response("Deleted", status=204, mimetype="application/json")
        except Exception as e:
            _logger.error(e)
            return Response("Server Error", status=500, mimetype="application/json")
    payment_delete.__doc__ = _lt("Delete Payment")

    #
    # PRIVATE METHODS
    #

    def _get_api(self, company, apikey, secretkey=False):
        domain = [('company_id', '=', company), ('api_key', '=', apikey)]
        if secretkey:
            domain.append(('secret_key', '=', secretkey))
        return self.env['payment.acquirer.jetcheckout.api'].sudo().search(domain, limit=1)

    def _get_hash(self, key, hash, id):
        hashed = base64.b64encode(hashlib.sha256(''.join([key.api_key, key.secret_key, str(id)]).encode('utf-8')).digest()).decode('utf-8')
        if hashed != hash:
            return False
        return hash

    def _get_installments(self, api, params):
        bin = getattr(params, 'bin')
        acquirer = self.env['payment.acquirer']._get_acquirer(company=api.company_id, providers=['jetcheckout'], limit=1)
        url = '%s/api/v1/prepayment/%sinstallment_options' % (acquirer._get_paylox_api_url(), bin and 'bin_' or '')
        data = {
            "application_key": acquirer.jetcheckout_api_key,
            "mode": acquirer._get_paylox_env(),
            "amount": getattr(params, 'amount', 0) or 0,
            "campaign": getattr(params, 'campaign_name', '') or '',
            "currency": getattr(params, 'currency', 'TRY') or 'TRY',
            "card_type": getattr(params, 'type', 'AllTypes') or 'AllTypes',
            "language": "tr",
        }
        if bin:
            data.update({"bin": bin})

        response = requests.post(url, data=json.dumps(data))
        if response.status_code == 200:
            result = response.json()
            if result['response_code'] == "00":
                installments = result['installments'] if bin else result['installment_options']
                return {
                    'installments': [{
                        'family': installment['card_family'],
                        'logo': installment['card_family_logo'],
                        'currency': installment['currency'],
                        'campaign': installment['campaign_name'],
                        'period': installment['inst_period'],
                        'type': None if bin else installment['card_type'],
                        'excluded': None if bin else installment['excluded_bins'],
                        'options': [{
                            'count': i['installment_count'],
                            'amount': i['installment_amount'],
                            'rate_cost': i['cost_rate'],
                            'rate_customer': i['customer_rate'],
                            'plus_count': i['plus_installment'],
                            'plus_desc': i['plus_installment_description'],
                            'min_amount': i['min_amount'],
                            'max_amount': i['max_amount'],
                            'min_rate_customer': i['min_customer_rate'],
                            'max_rate_customer': i['max_customer_rate'],
                        } for i in installment['installments']],
                    } for installment in installments]
                }
            raise Exception(result.get('message', _('An error occured. Please try again.')))
        raise Exception(_('An error occured. Please try again.'))

    def _create_transaction(self, api, hash, params):
        if hasattr(params.partner, 'country'):
            country = self.env['res.country'].sudo().search([('code', '=', params.partner.country)], limit=1)
        else:
            country = False

        if country and hasattr(params.partner, 'state'):
            state = self.env['res.country.state'].sudo().search([('country_id', '=', country.id), ('code', '=', params.partner.state)], limit=1)
        else:
            state = False

        type = getattr(params, 'type', False) or 'virtual_pos'
        codes = hasattr(params, 'methods') and params.methods or []
        method = ''
        providers = []
        for code in codes:
            if not type and code == 'bank':
                providers.append('transfer')
            else:
                providers.append('jetcheckout')
        if len(codes) == 1:
            method = codes[0]

        company = api.company_id
        if hasattr(params, 'company'):
            company = self.env['res.company'].sudo().search([('vat', '=', params.company.vat), ('parent_id', '=', company.id)])
            if not company:
                raise Exception('Company cannot be found')

        acquirer = self.env['payment.acquirer']._get_acquirer(company=company, providers=providers, limit=1)
        values = {
            'state': 'draft',
            'amount': params.amount,
            'company_id': company.id,
            'acquirer_id': acquirer.id,
            'partner_id': api.partner_id.id,
            'currency_id': company.currency_id.id,
            'jetcheckout_ip_address': params.partner.ip_address,
            'jetcheckout_payment_type': type,
            'jetcheckout_api_ok': True,
            'jetcheckout_api_hash': hash,
            'jetcheckout_api_id': params.id,
            'jetcheckout_api_method': method,
            'jetcheckout_api_order': params.order.name,
            'jetcheckout_api_html': getattr(params, 'html', False) or False,
            'jetcheckout_api_contact': getattr(params.partner, 'contact', False) or False,
            'jetcheckout_date_expiration': getattr(params, 'expiration', False) or False,
            'jetcheckout_campaign_name': getattr(params, 'campaign', False) or False,
        }

        if getattr(params.url, 'card', None):
            values.update({'jetcheckout_api_card_result_url': params.url.card.result})

        if getattr(params.url, 'bank', None):
            values.update({'jetcheckout_api_bank_result_url': params.url.bank.result})
            if getattr(params.url.bank, 'webhook', None):
                values.update({'jetcheckout_api_bank_webhook_url': params.url.bank.webhook})

        if getattr(params.url, 'credit', None):
            values.update({'jetcheckout_api_credit_result_url': params.url.credit.result})

        products = getattr(params.order, 'products', [])
        if products:
            will_create_product = values['jetcheckout_payment_type'] == 'virtual_pos'
            product_ids = []
            if will_create_product:
                prods = self.env['product.product'].sudo()
                for product in products:
                    prod = prods.search([
                        #('type', '=', 'product'),
                        ('type', '=', 'consu'),
                        ('default_code', '=', product),
                        '|', ('company_id', '=', company.id),
                            ('company_id', '=', False)
                    ])
                    if not prod:
                        prod = prods.create({
                            #'type': 'product',
                            'type': 'consu',
                            'name': product.name,
                            'default_code': product.code,
                        })
                    product_ids.append((0, 0, {
                        'product_id': prod.id,
                        'qty': product.qty,
                        'name': product.name,
                        'code': product.code,
                        'price': product.price,
                        'categ': getattr(product, 'categ', False) or False,
                        'brand': getattr(product, 'brand', False) or False,
                    }))
            else:
                for product in products:
                    product_ids.append((0, 0, {
                        'qty': product.qty,
                        'name': product.name,
                        'code': product.code,
                        'price': product.price,
                        'categ': getattr(product, 'categ', False) or False,
                        'brand': getattr(product, 'brand', False) or False,
                    }))

            values.update({'paylox_product_ids': product_ids})
            #values.update({'paylox_product_ids': ','.join(list(map(lambda x: x.name, products)))})

        tx = self.env['payment.transaction'].sudo().create(values)
        tx.write({
            'partner_name': params.partner.name,
            'partner_vat': params.partner.vat,
            'partner_email': params.partner.email,
            'partner_address': params.partner.address,
            'partner_phone': params.partner.phone,
            'partner_zip': getattr(params.partner, 'zip', '') or '',
            'partner_city': getattr(params.partner, 'city', '') or '',
            'partner_country_id': country and country.id or False,
            'partner_state_id': state and state.id or False,
        })

    def _get_transaction_from_hash(self, company, hash):
        return self.env['payment.transaction'].sudo().search([('company_id', '=', company), ('jetcheckout_api_hash', '=', hash)], limit=1)

    def _get_transaction_from_token(self, token):
        return self.env['payment.transaction'].sudo().search([('jetcheckout_order_id', '=', token)], limit=1)

    def _get_transaction_result(self, tx):
        return {
            'transaction': {
                'state': tx.state,
                'provider': tx.acquirer_id.provider,
                'virtual_pos_name': tx.jetcheckout_vpos_name or '',
                'order_id': tx.jetcheckout_order_id or '',
                'transaction_id': tx.jetcheckout_transaction_id or '',
                'message': tx.state_message if not tx.state == 'done' else _('Transaction is successful.'),
                'partner': {
                    'name': tx.partner_id.name or '',
                    'ip_address': tx.jetcheckout_ip_address or '',
                },
                'card': {
                    'name': tx.jetcheckout_card_name or '',
                    'number': tx.jetcheckout_card_number or '',
                    'type': tx.jetcheckout_card_type or '',
                    'program': tx.jetcheckout_card_program or '',
                    'family': tx.jetcheckout_card_family or '',
                },
                'credit': {
                    'bank': tx.jetcheckout_payment_type_credit_bank_code or '',
                },
                'amounts': {
                    'amount': tx.amount,
                    'raw': tx.jetcheckout_payment_amount,
                    'fees': tx.fees,
                    'installment': {
                        'amount': tx.jetcheckout_installment_amount,
                        'count': tx.jetcheckout_installment_count,
                        'description': tx.jetcheckout_installment_description,
                    },
                    'commission': {
                        'cost': {
                            'rate': tx.jetcheckout_commission_rate,
                            'amount': tx.jetcheckout_commission_amount,
                        },
                        'customer': {
                            'rate': tx.jetcheckout_customer_rate,
                            'amount': tx.jetcheckout_customer_amount,
                        }
                    },
                },
            }
        }

    def _cancel_transaction(self, tx):
        if not tx.state == 'cancel':
            tx._paylox_cancel()

    def _refund_transaction(self, tx, amount):
        tx._paylox_refund(amount)

    def _expire_transaction(self, tx):
        tx._paylox_expire()

    def _delete_transaction(self, tx):
        tx.unlink()

    def _query_transaction(self, tx):
        vals = tx._paylox_query()
        del vals['currency_id']
        return vals
