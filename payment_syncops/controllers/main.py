# -*- coding: utf-8 -*-
import io
import json
import base64
import pytz
from datetime import datetime
from urllib.parse import urlparse

from odoo import http, fields, _
from odoo.exceptions import ValidationError
from odoo.http import content_disposition, request, Response
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT
from odoo.tools.misc import xlsxwriter, formatLang
from odoo.addons.payment_jetcheckout_system.controllers.main import PayloxSystemController as Controller


class PayloxSyncopsController(Controller):

    def _connector_auth(self, header):
        code = header.split(' ', 1)[1]
        auth = base64.b64decode(code).decode('utf-8')
        username, password = auth.split(':', 1)
        connector = request.env['syncops.connector'].sudo().search([
            ('active', '=', True),
            ('connected', '=', True),
            ('username', '=', username),
            ('token', '=', password),
        ], limit=1)
        return connector

    def _connector_prepare_transactions(self, tx, tz=None):
        tz = tz or pytz.timezone('Europe/Istanbul')
        offset = tz.utcoffset(fields.Datetime.now())
        branch = tx.acquirer_id._get_branch_line(name=tx.jetcheckout_vpos_name, user=tx.create_uid)
        values = {
            'id': tx.id,
            'ref': tx.jetcheckout_order_id,
            'state': tx.state,
            'partner_ref': tx.partner_id.ref or '',
            'partner_name': tx.partner_id.name or '',
            'card_6': tx.jetcheckout_card_number[:6] if tx.jetcheckout_card_number else '',
            'card_4': tx.jetcheckout_card_number[-4:] if tx.jetcheckout_card_number else '',
            'vpos_id': tx.jetcheckout_vpos_id or 0,
            'bank_payment_day': 1,
            'installment_count': tx.jetcheckout_installment_count,
            'installment_code': tx.jetcheckout_campaign_name or '',
            'payment_date': (tx.create_date + offset).strftime('%Y-%m-%d'),
            'payment_time': (tx.create_date + offset).strftime('%H:%M:%S'),
            'currency_code': tx.currency_id.name or '',
            'payment_amount': tx.amount,
            'payment_net_amount': tx.jetcheckout_payment_amount,
            'plus_installment': tx.jetcheckout_installment_plus,
            'payment_deferral': 0,
            'bank_id': 0,
            'bank_name': '',
            'refund_payment_id': '',
            'refund_currency_code': '',
            'refund_date': '',
            'refund_time': '',
            'branch_code': branch and branch.account_code or '',
            'company_code': tx.company_id.partner_id.ref or '',
            'payment_ref': '03',
        }
        if tx.source_transaction_id:
            values.update({
                'refund_payment_id': tx.source_transaction_id.id,
                'refund_currency_code': tx.source_transaction_id.currency_id.name,
                'refund_date': (tx.source_transaction_id.create_date + offset).strftime('%Y-%m-%d'),
                'refund_time': (tx.source_transaction_id.create_date + offset).strftime('%H:%M:%S'),
            })
        return values

    def _connector_get_partner(self, partner=None):
        partner = partner and partner.commercial_partner_id or request.env.user.sudo().partner_id.commercial_partner_id
        return {
            'name': partner.name,
            'vat': partner.vat,
            'ref': partner.ref,
            'connector': False,
        }
        #TODO check cache first
        data = self._get('syncops')
        if data:
            return {
                'name': data['name'],
                'vat': data['vat'],
                'ref': data['ref'],
                'connector': True,
            }
        else:
            partner = partner and partner.commercial_partner_id or request.env.user.sudo().partner_id.commercial_partner_id
            return {
                'name': partner.name,
                'vat': partner.vat,
                'ref': partner.ref,
                'connector': False,
            }

    def _connector_get_partner_balance(self, vat, ref, company=None):
        balances, show_total = {}, False
        company = company or request.env.company
        company_id = company.sudo().partner_id.ref
        result = request.env['syncops.connector'].sudo()._execute('payment_get_partner_balance', params={
            'company_id': company_id,
            'vat': vat,
            'ref': ref,
        }, company=company)
        if result:
            for res in result:
                currency_name = res.get('currency_name', '')
                currency = request.env['res.currency'].sudo().with_context(active_test=False).search([('name', '=', currency_name)], limit=1)
                if not currency:
                    continue

                amount = isinstance(res.get('amount'), float) and res['amount'] or 0
                if currency_name in balances:
                    amount += balances[currency_name]['value']
                else:
                    balances[currency_name] = {
                        'note': res.get('note', ''),
                    }

                amount_formatted = formatLang(request.env, amount, currency_obj=currency)
                if 'amount_total' in res:
                    show_total = True
                    amount_total = isinstance(res['amount_total'], float) and res['amount_total'] or 0
                    amount_total = formatLang(request.env, amount_total, currency_obj=currency)
                else:
                    amount_total = formatLang(request.env, 0, currency_obj=currency)

                balances[currency_name].update({
                    'value': amount,
                    'amount': amount_formatted,
                    'amount_total': amount_total,
                })

        if not balances:
            amount = 0
            amount_formatted = formatLang(request.env, 0, currency_obj=company.currency_id)
            amount_total = formatLang(request.env, 0, currency_obj=company.currency_id)

            balances[company.currency_id.name] = {
                'value': amount,
                'amount': amount_formatted,
                'amount_total': amount_total,
                'note': '',
            }

        return list(balances.values()), show_total

    def _connector_get_partner_ledger(self, vat, ref, date_start, date_end, company=None):
        company = company or request.env.company
        result = request.env['syncops.connector'].sudo()._execute('payment_get_partner_ledger', params={
            'company_id': company.sudo().partner_id.ref,
            'vat': vat,
            'ref': ref,
            'date_start': date_start.strftime('%Y-%m-%d') + ' 00:00:00',
            'date_end': date_end.strftime('%Y-%m-%d') + ' 23:59:59',
        }, company=company)
        if result == None:
            return {}

        currencies = {}
        for res in result:
            currency_name = res['currency_name']
            currency = request.env['res.currency'].sudo().with_context(active_test=False).search([('name', '=', currency_name)], limit=1)
            if not currency:
                continue

            lines = [{
                'date': res.get('date', ''),
                'due_date': res.get('due_date', ''),
                'type': res.get('type', ''),
                'name': res.get('name', ''),
                'description': res.get('description', ''),
                'amount': res.get('amount', 0),
                'balance': res.get('balance', 0),
                'currency': {
                    'id' : currency.id,
                    'name' : currency.name,
                    'position' : currency.position,
                    'symbol' : currency.symbol,
                    'precision' : currency.decimal_places,
                },
            }]
            if currency_name in currencies:
                currencies[currency_name].extend(lines)
            else:
                currencies[currency_name] = lines
        return currencies

    def _connector_can_show_partner_ledger(self, company=None):
        company = company or request.env.company
        return request.env['syncops.connector'].sudo().count('payment_get_partner_ledger', company=company)

    def _connector_can_show_partner_balance(self, company=None):
        company = company or request.env.company
        return request.env['syncops.connector'].sudo().count('payment_get_partner_balance', company=company)

    def _connector_can_access_partner_list(self, company=None):
        user = request.env.user.sudo()
        company = company or request.env.company
        return not user.share and company.id in user.company_ids.ids and request.env['syncops.connector'].sudo().count('payment_get_partner_list', company=company)

    def _connector_can_access_partner_list_search(self, company=None):
        user = request.env.user.sudo()
        company = company or request.env.company
        return not user.share and company.id in user.company_ids.ids and request.env['syncops.connector'].sudo().count('payment_get_partner_list_search', company=company)

    def _connector_can_access_partner_list_page(self, company=None):
        user = request.env.user.sudo()
        company = company or request.env.company
        return not user.share and company.id in user.company_ids.ids and request.env['syncops.connector'].sudo().count('payment_get_partner_list_page', company=company)

    def _get_tx_values(self, **kwargs):
        vals = super()._get_tx_values(**kwargs)
        user = request.env.user
        company = request.env.company
        connector_partner = self._get('syncops')
        partner = self._get_partner(kwargs['partner'], parent=True)
        if 'number' in kwargs.get('card', {}) and company.syncops_check_card:# and user.has_group('payment_syncops.group_check_card'):
            vat = connector_partner and connector_partner['vat'] or partner.vat
            result, message = self.env['syncops.connector'].sudo()._execute('other_get_ozan_card', params={
                'vat': vat,
                'number': str(kwargs['card']['number']),
            }, company=self.env.company, message=True)
            if result is None:
                raise Exception(message)

        path = urlparse(request.httprequest.referrer).path
        if path == '/my/payment':
            if connector_partner:
                vals.update({
                    'partner_name': connector_partner['name'],
                    'jetcheckout_connector_partner_name': connector_partner['name'],
                    'jetcheckout_connector_partner_vat': connector_partner['vat'],
                    'jetcheckout_connector_partner_ref': connector_partner['ref'],
                })
            else:
                if  not user.share and user.partner_id.id == kwargs.get('partner', 0) \
                    and company.syncops_payment_page_partner_required \
                    and request.env['syncops.connector'].sudo().count('payment_get_partner_list', company=company):
                        raise ValidationError(_('Please select a partner'))

        connector = request.env['syncops.connector'].sudo().search_count([
            ('company_id', '=', company.id),
            ('active', '=', True),
            ('connected', '=', True),
        ])
        if connector:
            vals.update({
                'jetcheckout_connector_ok': True,
            })
        return vals

    def _prepare(self, company=None, partner=None, **kwargs):
        self._del('syncops')
        values = super()._prepare(company=company, partner=partner, **kwargs)
        partner = self._connector_get_partner(values['partner'])
        balances, show_total = self._connector_get_partner_balance(partner['vat'], partner['ref'], company)
        show_balance = self._connector_can_show_partner_balance()
        show_ledger = self._connector_can_show_partner_ledger()
        show_partners = self._connector_can_access_partner_list(company)

        values.update({
            'balances': balances,
            'show_total': show_total,
            'show_balance': show_balance,
            'partner_connector': partner,
            'partner_name': partner['name'],
        })
        if request.httprequest.path == '/my/payment':
            values.update({
                'show_ledger': show_ledger,
                'show_partners': show_partners,
                'show_reset': True,
            })
        return values

    @http.route(['/my/payment/ledger'], type='http', auth='user', website=True)
    def page_syncops_ledger(self, **kwargs):
        values = self._prepare()
        year = datetime.now().year
        date_start = datetime(year, 1, 1)
        date_end = datetime(year, 12, 31)
        values.update({
            'date_start': date_start.strftime('%d-%m-%Y'),
            'date_end': date_end.strftime('%d-%m-%Y'),
            'date_format': 'DD-MM-YYYY'
        })

        if request.env.lang:
            lang = request.env.lang
            values.update({
                'date_locale': lang[:2],
            })

        return request.render('payment_syncops.page_ledger', values)

    @http.route(['/my/payment/partners/ledger/list'], type='json', auth='user', website=True)
    def page_syncops_ledger_list(self, **kwargs):
        date_start = kwargs.get('start')
        if not date_start:
            return {'error': _('Start date cannot be empty')}

        date_end = kwargs.get('end')
        if not date_end:
            return {'error': _('End date cannot be empty')}

        date_format = kwargs.get('format')
        if not date_format:
            return {'error': _('Date format cannot be empty')}

        partner_connector = self._connector_get_partner()
        vat = partner_connector['vat']
        ref = partner_connector['ref']
        date_format = date_format.replace('DD', '%d').replace('MM', '%m').replace('YYYY', '%Y')
        date_start = datetime.strptime(date_start, date_format)
        date_end = datetime.strptime(date_end, date_format)
        if date_start > date_end:
            return {'error': _('Start date cannot be later than end date')}

        rows = self._connector_get_partner_ledger(vat, ref, date_start, date_end)
        ledgers = []
        for key in rows.keys():
            ledgers.extend(rows[key])

        return {
            'ledgers': ledgers
        }

    @http.route(['/my/payment/partners'], type='json', auth='user', website=True)
    def page_syncops_partners(self, **kwargs):
        if self._connector_can_access_partner_list_page():
            result = request.env['syncops.connector'].sudo()._execute('payment_get_partner_list_page', params={
                'company': request.env.company.sudo().partner_id.ref,
                'search': kwargs.get('search', False),
                'page': kwargs.get('page', 1),
                'size': 20,
            })
            if not result == None:
                return result

        elif self._connector_can_access_partner_list_search():
            search =  kwargs.get('search', False)
            if not search:
                return []

            result = request.env['syncops.connector'].sudo()._execute('payment_get_partner_list_search', params={
                'company': request.env.company.sudo().partner_id.ref,
                'search': search,
            })
            if not result == None:
                return result

        elif self._connector_can_access_partner_list():
            result = request.env['syncops.connector'].sudo()._execute('payment_get_partner_list', params={
                'company': request.env.company.sudo().partner_id.ref,
            })
            if not result == None:
                return result

        return []

    @http.route(['/my/payment/partners/select'], type='json', auth='user', website=True)
    def page_syncops_partners_select(self, **kwargs):
        if not self._connector_can_access_partner_list():
            return False

        self._set('syncops', {
            'name': kwargs.get('company'),
            'vat': kwargs.get('vat'),
            'ref': kwargs.get('ref'),
        })

        balances, show_total = self._connector_get_partner_balance(kwargs.get('vat'), kwargs.get('ref'))
        show_balance = self._connector_can_show_partner_balance()
        show_ledger = self._connector_can_show_partner_ledger()
        return {
            'name': kwargs.get('company'),
            'campaign': kwargs.get('campaign'),
            'balances': balances,
            'show_total': show_total,
            'show_balance': show_balance,
            'show_ledger': show_ledger,
        }

    @http.route(['/my/payment/partners/reset'], type='json', auth='user', website=True)
    def page_syncops_partners_reset(self, **kwargs):
        self._del('syncops')
        partner = request.env.user.partner_id.commercial_partner_id
        balances, show_total = self._connector_get_partner_balance(vat=partner.vat, ref=partner.ref)
        show_balance = self._connector_can_show_partner_balance()
        show_ledger = self._connector_can_show_partner_ledger()
        return {
            'name': partner.name,
            'campaign': partner.campaign_id.name,
            'balances': balances,
            'show_total': show_total,
            'show_balance': show_balance,
            'show_ledger': show_ledger,
        }

    @http.route(['/syncops/payment/transactions'], type='http', auth='public', methods=['GET'], csrf=False, sitemap=False, save_session=False, website=True)
    def page_syncops_transactions(self, **data):
        headers = request.httprequest.headers
        if 'Authorization' not in headers:
            return Response('Access Denied', status=401)

        connector = self._connector_auth(headers['Authorization'])
        if not connector:
            return Response('Access Denied', status=401)

        response = []
        if data:
            now = fields.Datetime.now()
            date_start = datetime.strptime(data['payment_date_start'], DT) if 'payment_date_start' in data else now
            date_end = datetime.strptime(data['payment_date_end'], DT) if 'payment_date_end' in data else now
            tz = pytz.timezone('Europe/Istanbul')
            offset = tz.utcoffset(now)
            domain = [
                ('company_id', 'in', connector.get_company_ids()),
                ('create_date', '>=', date_start - offset),
                ('create_date', '<=', date_end - offset),
                ('jetcheckout_payment_type', '=', 'virtual_pos'),
            ]
            if 'payment_type' in data:
                if data['payment_type'] == 'payment':
                    domain.extend([('state', '=', 'done'), ('source_transaction_id', '=', False)])
                elif data['payment_type'] == 'cancel':
                    domain.extend([('state', '=', 'cancel'), ('source_transaction_id', '=', False)])
                elif data['payment_type'] == 'refund':
                    domain.extend([('state', '=', 'done'), ('source_transaction_id', '!=', False)])
                else:
                    domain.extend([('state', 'in', ('done', 'cancel'))])
            else:
                domain.extend([('state', 'in', ('done', 'cancel'))])

            transactions = request.env['payment.transaction'].sudo().search(domain)
            for transaction in transactions:
                values = self._connector_prepare_transactions(transaction)
                response.append(values)

        headers = [('Content-Type', 'application/json; charset=utf-8'), ('Cache-Control', 'no-store')]
        return request.make_response(json.dumps(response), headers)

    @http.route(['/syncops/payment/transactions/xlsx'], type='http', auth='user', methods=['GET'], sitemap=False, website=True)
    def page_syncops_transactions_xlsx(self, **data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        headers = {
            'id': 'PAYMENTID',
            'ref': 'REFERENCECODE',
            'partner_ref': 'CUST_ERP_CODE',
            'id': 'CUST_ERP_NAME',
            'card_6': 'CARD_6',
            'card_4': 'CARD_4',
            'vpos_id': 'VPOSID',
            'bank_payment_day': 'BANK_PAYMENT_DAY',
            'state': 'STATUS',
            'installment_count': 'PERIOD',
            'installment_code': 'PERIOD_CODE',
            'payment_date': 'PAYMENTDATE',
            'payment_time': 'PAYMENTTIME',
            'currency_code': 'CURRENCYCODE',
            'payment_amount': 'PROCCESSAMOUNT',
            'payment_net_amount': 'PROCCESSNETAMOUN',
            'plus_installment': 'PLUS_PERIOD',
            'payment_deferral': 'PAYMENT_DEFERRAL',
            'bank_id': 'BANKID',
            'bank_name': 'BANK_NAME',
            'branch_code': 'HKONT',
            'refund_payment_id': 'REV_PAYMENTID',
            'refund_currency_code': 'REV_CURRENCYCODE',
            'refund_date': 'REV_DATE',
            'refund_time': 'REV_TIME',
            'company_code': 'BRANCH_CODE',
            'payment_ref': 'SOURCEID',
        }
        for i, col in enumerate(headers.values()):
            worksheet.write(0, i, col)

        transactions = request.env['payment.transaction'].sudo().search([
            ('id', 'in', list(map(int, data[''].split(',')))),
            ('jetcheckout_payment_type', '=', 'virtual_pos'),
            ('company_id', '=', request.env.user.company_ids.ids)
        ])
        row = 0
        for transaction in transactions:
            row += 1
            values = self._connector_prepare_transactions(transaction)
            for i, key in enumerate(headers.keys()):
                worksheet.write(row, i, values[key])
        workbook.close()

        xlsx = output.getvalue()
        headers = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition('Transactions.xlsx'))
        ]
        return request.make_response(xlsx, headers=headers)
