# -*- coding: utf-8 -*-
import re
import uuid
import json
import base64
import hashlib
import requests

from odoo import api, fields, models, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_round
from .rpc import rpc


class PaymentPayloxTerms(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.term'
    _description = 'Paylox Terms'

    company_id = fields.Many2one('res.company')
    partner_id = fields.Many2one('res.partner')
    domain = fields.Char()


class PaymentPayloxPrestatus(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.prestatus'
    _description = 'Paylox Pre-Status'

    tx_id = fields.Many2one('payment.transaction', required=True)
    order_id = fields.Char(required=True, string='Order Reference')
    transaction_id = fields.Char(required=True, string='Transaction ID')

    def confirm(self):
        self.tx_id.write({
            'jetcheckout_order_id': self.order_id,
            'jetcheckout_transaction_id': self.transaction_id,
        })
        return self.tx_id.paylox_query()


class PaymentPayloxStatus(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.status'
    _description = 'Paylox Status'

    date = fields.Datetime(readonly=True)
    vpos_id = fields.Integer(readonly=True)
    vpos_name = fields.Char(readonly=True)
    vpos_ref = fields.Char(readonly=True)
    vpos_code = fields.Char(readonly=True)
    successful = fields.Boolean(readonly=True)
    completed = fields.Boolean(readonly=True)
    cancelled = fields.Boolean(readonly=True)
    preauth = fields.Boolean(readonly=True, string='Pre-Authorization')
    postauth = fields.Boolean(readonly=True, string='Post-Authorization')
    threed = fields.Boolean(readonly=True)
    currency_id =fields.Many2one('res.currency', readonly=True)
    amount = fields.Monetary(readonly=True)
    commission_amount = fields.Monetary(readonly=True)
    commission_rate = fields.Float(readonly=True)
    customer_amount = fields.Monetary(readonly=True, string='Customer Commission Amount')
    customer_rate = fields.Float(readonly=True, string='Customer Commission Rate')
    auth_code = fields.Char(readonly=True)
    card_family = fields.Char(readonly=True)
    card_program = fields.Char(readonly=True)
    bin_code = fields.Char(readonly=True)
    service_ref_id = fields.Char(readonly=True)
    service_code = fields.Char(readonly=True)
    service_message = fields.Char(readonly=True)


class PaymentPayloxRefund(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.refund'
    _description = 'Paylox Refund'

    transaction_id = fields.Many2one('payment.transaction', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)
    total = fields.Monetary(readonly=True, required=True)
    amount = fields.Monetary()

    def confirm(self):
        if self.amount > self.total:
            raise UserError(_('Refund amount cannot be higher than total amount'))
        self.transaction_id._paylox_api_refund(amount=self.amount)
        return {'type': 'ir.actions.act_window_close'}

    def draft(self):
        if self.amount > self.total:
            raise UserError(_('Refund amount cannot be higher than total amount'))
        self.transaction_id._paylox_refund_postprocess(amount=self.amount)
        return {'type': 'ir.actions.act_window_close'}


class PaymentPayloxBank(models.Model):
    _name = 'payment.acquirer.jetcheckout.bank'
    _description = 'Paylox Banks'
    _order = 'sequence'

    acquirer_id = fields.Many2one('payment.acquirer')
    sequence = fields.Integer()
    logo = fields.Image()
    name = fields.Char(required=True)
    iban_number = fields.Char(string='IBAN')
    account_number = fields.Char()
    branch = fields.Char()
    color = fields.Char()


class PaymentPayloxCampaign(models.Model):
    _name = 'payment.acquirer.jetcheckout.campaign'
    _description = 'Paylox Campaigns'

    acquirer_id = fields.Many2one('payment.acquirer')
    name = fields.Char(required=True)


class PaymentPayloxJournal(models.Model):
    _name = 'payment.acquirer.jetcheckout.journal'
    _description = 'Paylox Journals'

    acquirer_id = fields.Many2one('payment.acquirer')
    name = fields.Char(required=True, readonly=True)
    journal_id = fields.Many2one('account.journal')
    partner_id = fields.Many2one('res.partner', domain=[('is_company','=',True)])
    currency_id = fields.Many2one('res.currency', related='journal_id.currency_id', readonly=True, store=True)
    company_id = fields.Many2one('res.company', ondelete='cascade', readonly=True, default=lambda self: self.env.company)
    website_id = fields.Many2one('website', ondelete='cascade', readonly=True, default=lambda self: self.env.company.website_id)
    line_ids = fields.One2many('payment.acquirer.jetcheckout.journal.line', 'line_id', 'Lines')
    secondary_ok = fields.Boolean('Use Secondary Journals')
    res_id = fields.Integer(readonly=True)


class PaymentPayloxJournalLine(models.Model):
    _name = 'payment.acquirer.jetcheckout.journal.line'
    _description = 'Paylox Journal Lines'

    line_id = fields.Many2one('payment.acquirer.jetcheckout.journal')
    name = fields.Char(required=True)
    acquirer_id = fields.Many2one('payment.acquirer', related='line_id.acquirer_id', store=True)
    journal_id = fields.Many2one('account.journal', required=True)
    partner_id = fields.Many2one('res.partner', domain=[('is_company','=',True)], required=True)
    currency_id = fields.Many2one('res.currency', related='journal_id.currency_id', readonly=True, store=True)
    company_id = fields.Many2one('res.company', ondelete='cascade', readonly=True, default=lambda self: self.env.company)
    website_id = fields.Many2one('website', ondelete='cascade', readonly=True, default=lambda self: self.env.company.website_id)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    def _get_paylox_url(self):
        for acq in self:
            acq.paylox_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', self.env.company.name)

    @api.onchange('display_icon')
    def _compute_display_icon(self):
        for acq in self:
            if acq.display_icon:
                acq.display_icon_preview = '<i class="fa ' + acq.display_icon + '"></i>'
            else:
                acq.display_icon_preview = ''

    @api.depends('provider')
    def _compute_view_configuration_fields(self):
        """
        Override of payment to hide the credentials page.
        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda acq: acq.provider == 'transfer').write({'show_pre_msg': True})

    provider = fields.Selection(selection_add=[('jetcheckout', 'jetcheckout')], ondelete={'jetcheckout': 'set default'})
    currency_ids = fields.Many2many('res.currency', string='Currency')

    display_icon = fields.Char(groups='base.group_user')
    display_icon_preview = fields.Html(compute='_compute_display_icon', groups='base.group_user', sanitize=False)

    paylox_bank_ids = fields.One2many('payment.acquirer.jetcheckout.bank', 'acquirer_id', groups='base.group_user')
    jetcheckout_gateway_api = fields.Char(groups='base.group_user', readonly=True)
    jetcheckout_gateway_app = fields.Char(groups='base.group_user', readonly=True)
    jetcheckout_gateway_database = fields.Char(groups='base.group_user', readonly=True)
    jetcheckout_payment_page = fields.Boolean('Show Payment Page')
    jetcheckout_api_key = fields.Char(groups='base.group_user')
    jetcheckout_secret_key = fields.Char(groups='base.group_user')
    paylox_url = fields.Char(compute='_get_paylox_url')
    paylox_journal_ids = fields.One2many('payment.acquirer.jetcheckout.journal', 'acquirer_id', groups='base.group_user')
    paylox_campaign_ids = fields.One2many('payment.acquirer.jetcheckout.campaign', 'acquirer_id', groups='base.group_user')
    jetcheckout_terms = fields.Html(required_if_provider='jetcheckout', groups='base.group_user', sanitize=False, sanitize_attributes=False, sanitize_form=False)
    jetcheckout_no_terms = fields.Boolean('Hide Terms')
    jetcheckout_no_smart_buttons = fields.Boolean('Hide Smart Buttons')
    jetcheckout_username = fields.Char(readonly=True)
    jetcheckout_password = fields.Char(readonly=True)
    jetcheckout_user_id = fields.Integer(readonly=True)
    jetcheckout_api_name = fields.Char(readonly=True)
    jetcheckout_campaign_id = fields.Many2one('payment.acquirer.jetcheckout.campaign', string='Campaign', ondelete='set null', copy=False)
    jetcheckout_soft_pos_version = fields.Boolean()
    jetcheckout_soft_pos_email = fields.Char()

    @api.model
    def _get_acquirer(self, company=None, website=None, providers=None, limit=None, raise_exception=True):
        self = self.sudo()
        domain = [('state', 'in', ('enabled', 'test'))]
        if providers:
            domain.append(('provider', 'in', providers))
        if self.env['res.company'].search_count([]) > 1:
            company = company or self.env.company
            if isinstance(company, int):
                company = self.env['res.company'].browse(company)
            domain.append(('company_id', '=', company.id))
            if website and self.env['website'].search_count([('company_id', '=', company.id)]) > 1:
                domain.append(('website_id', '=', website.id))

        acquirer = self.search(domain, limit=limit, order='sequence')
        if not acquirer:
            if raise_exception:
                raise ValidationError(_('Payment acquirer not found. Please contact with system administrator'))
        return acquirer

    def _get_journal_line(self, name, ref=None):
        line = self.env['payment.acquirer.jetcheckout.journal'].search([
            ('acquirer_id', '=', self.id),
            ('name', '=', name)
        ], limit=1)

        subline = self.env['payment.acquirer.jetcheckout.journal.line']
        if not ref == None and line and line.secondary_ok:
            subline = subline.search([
                ('line_id', '=', line.id),
                ('name', '=', ref)
            ], limit=1)

        return subline or line

    def _get_campaign_name(self, pid):
        self.ensure_one()
        partner = self.env['res.partner'].sudo().browse(pid) if pid else self.env.user.partner_id.commercial_partner_id
        return partner.campaign_id.name or self.jetcheckout_campaign_id.name or ''

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'jetcheckout':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_jetcheckout.payment_method_jetcheckout').id

    def _get_paylox_api_url(self):
        self.ensure_one()
        return self.jetcheckout_gateway_api or 'https://api.jetcheckout.com'

    def _get_paylox_env(self):
        return 'P' if self.state == 'enabled' else 'T'

    def _render_paylox_terms(self, company, partner):
        domain = self.env.context.get('domain', '')
        if domain:
            parts = domain.split('/')
            domain = '//'.join([parts[0], parts[2]])
        terms = self.env['payment.acquirer.jetcheckout.term'].sudo().create({
            'company_id': company,
            'partner_id': partner,
            'domain': domain,
        })
        return self.env['mail.render.mixin']._render_template(self.jetcheckout_terms, 'payment.acquirer.jetcheckout.term', terms.ids, engine='inline_template')[terms.id]

    @api.model
    def paylox_s2s_form_process(self, kwargs):
        partner_id = int(kwargs['partner_id'])
        domain = [
            ('jetcheckout_card_holder','=',kwargs.get('cc_holder_name')),
            ('jetcheckout_card_number','=',kwargs.get('cc_number').replace(' ', '')),
            ('jetcheckout_card_expiry_month','=',kwargs.get('cc_expiry')[:2]),
            ('jetcheckout_card_expiry_year','=',kwargs.get('cc_expiry')[-2:]),
            ('jetcheckout_card_cvc','=',kwargs.get('cvc')),
            ('partner_id','=',partner_id)
        ]
        token = self.env['payment.token'].sudo().search(domain, limit=1)

        if token:
            token.jetcheckout_card_3d = kwargs.get('secure', True)
            token.jetcheckout_card_save = kwargs.get('save', False)
            token.jetcheckout_card_installment = kwargs.get('installment_id', '1')
            return token

        return self.env['payment.token'].sudo().create({
            'acquirer_id': int(kwargs['acquirer_id']),
            'acquirer_ref': kwargs.get('cc_holder_name'),
            'jetcheckout_card_holder': kwargs.get('cc_holder_name'),
            'jetcheckout_card_number': kwargs.get('cc_number').replace(' ', ''),
            'jetcheckout_card_expiry_month': kwargs.get('cc_expiry')[:2],
            'jetcheckout_card_expiry_year': kwargs.get('cc_expiry')[-2:],
            'jetcheckout_card_cvc': kwargs.get('cvc'),
            'jetcheckout_card_3d': kwargs.get('secure', True),
            'jetcheckout_card_save': kwargs.get('save', False),
            'jetcheckout_card_installment': kwargs.get('installment_id', '1'),
            'partner_id': partner_id,
            'name': 'XXXX-XXXX-XXXX-%s - %s' % (kwargs['cc_number'][-4:], kwargs['cc_holder_name'])
        })

    def paylox_s2s_form_validate(self, data):
        self.ensure_one()
        for field_name in ['cc_number', 'cvc', 'cc_holder_name', 'cc_expiry', 'installment_id']:
            if not data.get(field_name):
                return False
        return True

    def action_paylox_signin(self):
        self.ensure_one()
        wizard = self.env['payment.acquirer.jetcheckout.signin'].create({'acquirer_id': self.id})
        action = self.env.ref('payment_jetcheckout.action_signin').sudo().read()[0]
        action['res_id'] = wizard.id
        action['context'] = {'dialog_size': 'small'}
        return action

    def action_paylox_signup(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'https://app.jetcheckout.com/web/signup'
        }

    def action_paylox_signout(self):
        self.ensure_one()
        self.jetcheckout_username = False
        self.jetcheckout_password = False
        self.jetcheckout_user_id = False
        self.jetcheckout_api_key = False
        self.jetcheckout_secret_key = False
        self.jetcheckout_gateway_api = False
        self.jetcheckout_gateway_app = False
        self.jetcheckout_campaign_id = False
        self.paylox_campaign_ids = [(5, 0, 0)]
        self.paylox_journal_ids = [(5, 0, 0)]

    def action_paylox_campaign(self):
        self.ensure_one()
        self._paylox_api_vacuum()
        campaign = self.jetcheckout_campaign_id.name
        campaigns = self.env['payment.acquirer.jetcheckout.campaign'].search([('acquirer_id', '=', self.id)])
        line_ids = [(0, 0, {
            'acquirer_id': self.id,
            'campaign_id': False,
            'name': _('Default'),
            'is_active': not campaign,
        })] + [(0, 0, {
            'acquirer_id': self.id,
            'campaign_id': c.id,
            'name': c.name,
            'is_active': c.name == campaign,
        }) for c in campaigns]

        wizard = self.env['payment.acquirer.jetcheckout.api.campaigns'].create({'acquirer_id': self.id, 'line_ids': line_ids})
        action = self.env.ref('payment_jetcheckout.action_api_campaigns').sudo().read()[0]
        action['res_id'] = wizard.id
        action['context'] = {'dialog_size': 'small', 'create': False, 'delete': False}
        return action

    def action_paylox_pos(self):
        self.ensure_one()
        #pos = self.env['payment.acquirer.jetcheckout.api.poses'].create({'acquirer_id': self.id, 'application_id': self.jetcheckout_api_key})
        self._paylox_api_connect(pos=True)
        action = self.env.ref('payment_jetcheckout.action_api_pos').sudo().read()[0]
        action['domain'] = [('acquirer_id', '=', self.id)]
        action['context'] = {'default_acquirer_id': self.id, 'pos': True}
        return action

    def action_paylox_application(self):
        self.ensure_one()
        #app = self.env['payment.acquirer.jetcheckout.api.applications'].create({'acquirer_id': self.id})
        self._paylox_api_connect()
        action = self.env.ref('payment_jetcheckout.action_api_application').sudo().read()[0]
        action['domain'] = [('acquirer_id', '=', self.id)]
        action['context'] = {'default_acquirer_id': self.id, 'application': True}
        return action

    def action_payment(self, options={}, **kwargs):
        partner = kwargs['partner']
        currency = kwargs['currency']

        payment_type = kwargs.get('type', '')
        if payment_type == 'virtual_pos':
            rows = kwargs['installment']['rows']
            installment = kwargs['installment']['id']
            campaign = kwargs.get('campaign') or self.jetcheckout_campaign_id.name or ''

            amount = float(kwargs['amount'])
            rate = float(kwargs.get('discount', {}).get('single', 0))
            if rate > 0 and installment == 1:
                amount = amount * (100 - rate) / 100

            installment_type = kwargs.get('installment_type', 'i')
            if installment_type == 'c':
                index = kwargs['installment']['index']
                installment = next(filter(lambda x: x['id'] == installment, rows), None)
                installment = next(filter(lambda x: x['index'] == index, installment['ids']), None)
            elif installment_type == 'ct':
                index = kwargs['installment']['id']
                installment = next(filter(lambda x: x['id'] == index and x['campaign'] == campaign, rows), None)
            else:
                installment = next(filter(lambda x: x['id'] == installment, rows), None)

            amount_customer = amount * installment['crate'] / 100
            amount_total = float_round(amount + amount_customer, 2)
            amount_cost = float_round(amount_total * installment['corate'] / 100, 2)
            amount_integer = round(amount_total * 100)

            year = str(fields.Date.today().year)[:2]
            number = 'number' in kwargs['card'] and str(kwargs['card']['number']) or False
            token = 'token' in kwargs['card'] and kwargs['token'] or False
            hash = base64.b64encode(hashlib.sha256(''.join([self.jetcheckout_api_key, number or token.jetcheckout_ref, str(amount_integer), self.jetcheckout_secret_key]).encode('utf-8')).digest()).decode('utf-8')
            data = {
                "application_key": self.jetcheckout_api_key,
                "mode": self._get_paylox_env(),
                "campaign_name": campaign,
                "amount": amount_integer,
                "currency": currency.name,
                "installment_count": installment['count'],
                "expire_month": kwargs['card']['date'][:2],
                "expire_year": year + kwargs['card']['date'][-2:],
                "is_3d": kwargs.get('threed', True),
                "hash_data": hash,
                "language": "tr",
            }
            if number:
                data.update({'card_number': number})
            elif token and token.verified:
                data.update({'card_token': token.jetcheckout_ref})

            if getattr(partner, 'tax_office_id', False):
                data.update({'billing_tax_office': partner.tax_office_id.name})
            elif getattr(partner, 'paylox_tax_office', False):
                data.update({'billing_tax_office': partner.paylox_tax_office})

            if partner.vat:
                partner_vat = re.sub(r'[^\d]', '', partner.vat)
                if partner_vat and len(partner_vat) in (10, 11):
                    data.update({'billing_tax_number': partner_vat})

            order_id = str(uuid.uuid4())
            sale_id = int(kwargs.get('order', 0))
            invoice_id = int(kwargs.get('invoice', 0))

            #tx = self._get_transaction()
            tx = False
            vals = {
                'acquirer_id': self.id,
                'callback_hash': hash,
                'amount': amount_total,
                'fees': amount_cost,
                'operation': 'online_direct',
                'token_id': token and token.id or False,
                'jetcheckout_payment_type': payment_type,
                'jetcheckout_website_id': kwargs['website'].id,
                'jetcheckout_ip_address': tx and tx.jetcheckout_ip_address or kwargs['request']['address'] or request.httprequest.remote_addr,
                'jetcheckout_url_address': tx and tx.jetcheckout_url_address or kwargs['request']['referrer'] or request.httprequest.referrer,
                'jetcheckout_campaign_name': campaign,
                'jetcheckout_card_name': kwargs['card']['holder'],
                'jetcheckout_card_number': number and  ''.join([number[:6], '*'*6, number[-4:]]) or False,
                'jetcheckout_card_type': kwargs['card']['type'].capitalize(),
                'jetcheckout_card_family': kwargs['card']['family'].capitalize(),
                'jetcheckout_order_id': order_id,
                'jetcheckout_payment_amount': amount,
                'jetcheckout_installment_count': installment['count'],
                'jetcheckout_installment_plus': installment['plus'],
                'jetcheckout_installment_description': installment['idesc'],
                'jetcheckout_installment_amount': amount / installment['count'] if installment['count'] > 0 else amount,
                'jetcheckout_commission_rate': installment['corate'],
                'jetcheckout_commission_amount': amount_cost,
                'jetcheckout_customer_rate': installment['crate'],
                'jetcheckout_customer_amount': amount_customer,
                'jetcheckout_payment_ok': kwargs.get('payment', True),
            }

            #vals.update(self._get_tx_values(**kwargs))
            if tx:
                tx.write(vals)
            else:
                vals.update({
                    'acquirer_id': self.id,
                    'partner_id': partner.id,
                    'currency_id': currency.id,
                })
                tx = self.env['payment.transaction'].sudo().create(vals)

            if sale_id:
                tx.sale_order_ids = [(4, sale_id)]
                sale_order_id = self.env['sale.order'].sudo().browse(sale_id)
                billing_partner_id = sale_order_id.partner_invoice_id
                shipping_partner_id = sale_order_id.partner_shipping_id
                data.update({
                    "billing_address": {
                        "contactName": billing_partner_id.name,
                        "address": "%s %s/%s/%s" % (billing_partner_id.street, billing_partner_id.city, billing_partner_id.state_id and billing_partner_id.state_id.name or '', billing_partner_id.country_id and billing_partner_id.country_id.name or ''),
                        "city": billing_partner_id.state_id and billing_partner_id.state_id.name or "",
                        "country": billing_partner_id.country_id and billing_partner_id.country_id.name or "",
                    },
                    "shipping_address": {
                        "contactName": shipping_partner_id.name,
                        "address": "%s %s/%s/%s" % (shipping_partner_id.street, shipping_partner_id.city, shipping_partner_id.state_id and shipping_partner_id.state_id.name or '', shipping_partner_id.country_id and shipping_partner_id.country_id.name or ''),
                        "city": shipping_partner_id.state_id and shipping_partner_id.state_id.name or "",
                        "country": shipping_partner_id.country_id and shipping_partner_id.country_id.name or "",
                    },
                })

                if not float_compare(amount, sale_order_id.amount_total, 2):
                    customer_basket = [{
                        "id": line.product_id.default_code or str(line.product_id.id),
                        "name": line.product_id.name,
                        "description": line.name,
                        "qty": line.product_uom_qty,
                        "amount": line.price_total,
                        "category": line.product_id.categ_id.name,
                        "is_physical": line.product_id.type == 'product',
                    } for line in sale_order_id.order_line if line.price_total > 0]

                    if amount_customer > 0:
                        product = self.env.ref('payment_jetcheckout.product_commission').sudo()
                        customer_basket.append({
                            "id": product.default_code or str(product.id),
                            "name": product.display_name,
                            "description": product.name,
                            "qty": 1.0,
                            "amount": round(float_round(amount_customer, 2), 2), # used double round, because format_round seems not working
                            "category": product.categ_id.name,
                            "is_physical": False,
                        })
                    data.update({"customer_basket": customer_basket})

            elif invoice_id:
                tx.invoice_ids = [(4, invoice_id)]

            #self._set('tx', tx.id)

            fullname = tx.partner_name.split(' ', 1)
            address = []
            if tx.partner_city:
                address.append(tx.partner_city)
            if tx.partner_state_id:
                address.append(tx.partner_state_id.name)
            if tx.partner_country_id:
                address.append(tx.partner_country_id.name)

            success_url = '/payment/card/success' if 'successurl' not in kwargs or not kwargs['successurl'] else kwargs['successurl']
            fail_url = '/payment/card/fail' if 'failurl' not in kwargs or not kwargs['failurl'] else kwargs['failurl']
            data.update({
                "order_id": order_id,
                "card_holder_name": kwargs['card']['holder'],
                "cvc": kwargs['card']['code'],
                "success_url": "%s%s" % (kwargs['website']['domain'], success_url),
                "fail_url": "%s%s" % (kwargs['website']['domain'], fail_url),
                "customer":  {
                    "name": fullname[0],
                    "surname": fullname[-1],
                    "email": tx.partner_email,
                    "id": str(tx.partner_id.id),
                    "identity_number": tx.partner_id.vat,
                    "phone": tx.partner_phone,
                    "ip_address": tx.jetcheckout_ip_address or kwargs['request']['address'],
                    "postal_code": tx.partner_zip,
                    "company": tx.partner_id.parent_id and tx.partner_id.parent_id.name or "",
                    "address": "%s %s" % (tx.partner_address, "/".join(address)),
                    "city": tx.partner_state_id and tx.partner_state_id.name or "",
                    "country": tx.partner_country_id and tx.partner_country_id.name or "",
                },
            })

            if tx.token_id and not tx.token_id.verified:
                data.update({
                    "save_card": True,
                    "card_alias": tx.token_id.name,
                    "card_owner_key": tx.token_id.jetcheckout_ref,
                    "card_owner_email": tx.token_id.partner_id.email,
                })
                tx.token_id.write({
                    'jetcheckout_number': tx.jetcheckout_card_number,
                    'jetcheckout_type': kwargs['card']['type'],
                    'jetcheckout_holder': kwargs['card']['holder'],
                    'jetcheckout_family': kwargs['card']['family'],
                    'jetcheckout_expiry': kwargs['card']['date'],
                    'jetcheckout_security': kwargs['card']['code'],
                })

            if 'submerchant' in kwargs:
                data.update({
                    "is_submerchant_payment": True,
                    "submerchant_external_id": kwargs['submerchant']['ref'],
                    "submerchant_price": kwargs['submerchant']['price'],
                })
            
            if 'item' in kwargs:
                tx.write({
                    'jetcheckout_item_ids': [(4, kwargs['item'].id)],
                    'paylox_transaction_item_ids': [(0, 0, {
                        'item_id': kwargs['item'].id,
                        'ref': kwargs['item'].ref,
                        'amount': kwargs['amount'],
                    })]
                })

            #data.update(self._get_data_values(data, **kwargs))

            if options.get('simulate'):
                url = '%s/api/v1/payment/simulation' % self._get_paylox_api_url()
            
                response = requests.post(url, data=json.dumps(data))
                if response.status_code == 200:
                    result = response.json()
                    installment['crate'] = result['expected_customer_rate']
                    installment['corate'] = result['expected_cost_rate']
                    amount = float(kwargs['amount'])
                    amount_customer = amount * installment['crate'] / 100
                    amount_total = float_round(amount + amount_customer, 2)
                    amount_cost = float_round(amount_total * installment['corate'] / 100, 2)
                    amount_integer = round(amount_total * 100)
                    hash = base64.b64encode(hashlib.sha256(''.join([self.jetcheckout_api_key, number or token.jetcheckout_ref, str(amount_integer), self.jetcheckout_secret_key]).encode('utf-8')).digest()).decode('utf-8')
                    if result['response_code'] == "00":
                        tx.write({
                            'amount': amount_total,
                            'fees': amount_cost,
                            'callback_hash': hash,
                            'jetcheckout_payment_amount': amount,
                            'jetcheckout_commission_rate': installment['corate'],
                            'jetcheckout_commission_amount': amount_cost,
                            'jetcheckout_customer_rate': installment['crate'],
                            'jetcheckout_customer_amount': amount_customer,
                        })
                        data.update({
                            "hash_data": hash,
                            "amount": amount_integer,
                        })
                else:
                    tx.state = 'error'
                    message = _('%s (Error Code: %s)') % (response.reason, response.status_code)
                    tx.write({
                        'state': 'error',
                        'state_message': message,
                        'last_state_change': fields.Datetime.now(),
                    })
                    return {'error': message}

            url = '%s/api/v1/payment' % self._get_paylox_api_url()
            response = requests.post(url, data=json.dumps(data))
            if response.status_code == 200:
                result = response.json()
                txid = result['transaction_id']
                if result['response_code'] == "00307":
                    rurl = result['redirect_url']
                    tx.write({
                        'state': 'pending',
                        'state_message': _('Transaction is pending...'),
                        'acquirer_reference': txid,
                        'jetcheckout_transaction_id': txid,
                        'last_state_change': fields.Datetime.now(),
                    })
                    return {'url': '%s/%s' % (rurl, txid), 'id': tx.id}
                elif result['response_code'] == "00":
                    tx.write({
                        'acquirer_reference': txid,
                        'jetcheckout_transaction_id': txid,
                        'last_state_change': fields.Datetime.now(),
                    })
                    tx._paylox_query({
                        'successful': True,
                        'code': result.get('response_code', ''),
                        'message': result.get('message', ''),
                        'amount': result.get('amount', 0),
                        'customer_amount': result.get('commission_amount', 0),
                        'commission_rate': result.get('expected_cost_rate', 0),
                        'vpos_name': result.get('virtual_pos_name', ''),
                        'vpos_id': result.get('virtual_pos_id', 0),
                        'vpos_code': result.get('auth_code', ''),
                        'card_program': result.get('card_program', ''),
                        'card_family': result.get('card_family', ''),
                        'card_type': result.get('card_type', ''),
                        'bin_code': result.get('bin_code', ''),
                    })
                    return {'ok': True, 'id': tx.id}
                else:
                    tx.state = 'error'
                    message = _('%s (Error Code: %s)') % (result['message'], result['response_code'])
                    if result['response_code'] == "00124" and tx.token_id:
                        tx.token_id.verified = True
                        message += '\n' + _('Please check whether the card is verified.')

                    tx.write({
                        'state': 'error',
                        'state_message': message,
                        'acquirer_reference': txid,
                        'jetcheckout_transaction_id': txid,
                        'last_state_change': fields.Datetime.now(),
                    })
                    return {'error': message}
            else:
                tx.state = 'error'
                message = _('%s (Error Code: %s)') % (response.reason, response.status_code)
                tx.write({
                    'state': 'error',
                    'state_message': message,
                    'last_state_change': fields.Datetime.now(),
                })
                return {'error': message}
            return {}
        

    def _rpc(self, *args):
        if not len(self) == 1:
            return

        url = self.jetcheckout_gateway_app or 'https://app.jetcheckout.com/jsonrpc'
        database = self.jetcheckout_gateway_database or 'jetcheckout'
        return rpc.execute(url, database, self.jetcheckout_user_id, self.jetcheckout_password, *args)

    def _paylox_api_vacuum(self):
        self = self.with_context(no_sync=True)
        self.env['payment.acquirer.jetcheckout.api.application'].search([('acquirer_id', '=', self.id)]).unlink()
        self.env['payment.acquirer.jetcheckout.api.pos'].search([('acquirer_id', '=', self.id)]).unlink()
        self.env['payment.acquirer.jetcheckout.api.campaign'].search([('acquirer_id', '=', self.id)]).unlink()
        self.env['payment.acquirer.jetcheckout.api.campaigns'].search([('acquirer_id', '=', self.id)]).unlink()
        self.env['payment.acquirer.jetcheckout.api.installment'].search([('acquirer_id', '=', self.id)]).unlink()
        self.env['payment.acquirer.jetcheckout.api.excluded'].search([('acquirer_id', '=', self.id)]).unlink()
        self.env['payment.acquirer.jetcheckout.api.bank'].search([('acquirer_id', '=', self.id)]).unlink()
        self.env['payment.acquirer.jetcheckout.api.family'].search([('acquirer_id', '=', self.id)]).unlink()
        self.env['payment.acquirer.jetcheckout.api.provider'].search([('acquirer_id', '=', self.id)]).unlink()
        self.env['payment.acquirer.jetcheckout.api.currency'].search([('acquirer_id', '=', self.id)]).unlink()

    def _paylox_api_create_currencies(self):
        currency_table = self.env['payment.acquirer.jetcheckout.api.currency']
        currencies = self._rpc('res.currency', 'search_read', [])
        for currency in currencies:
            currency_table.create({
                'acquirer_id': self.id,
                'res_id': currency['id'],
                'name': currency['name'],
            })
        return {item['res_id']: item['id'] for item in currency_table.search_read([], ['id', 'res_id'])}

    def _paylox_api_create_providers(self):
        providers = self._rpc('jet.payment.org', 'search_read', [])
        pos_infra_ids = [provider['virtual_pos_infraid'][0] for provider in providers]
        pos_infras = self._rpc('jet.virtual.pos.infra', 'search_read', [('id', 'in', pos_infra_ids)])
        provider_table = self.env['payment.acquirer.jetcheckout.api.provider']
        for provider in providers:
            vals = {
                'acquirer_id': self.id,
                'res_id': provider['id'],
                'code': provider['virtual_pos_infraid'][1],
                'name': provider['name'],
            }

            pos_infra = list(filter(lambda x: x['id'] == provider['virtual_pos_infraid'][0], pos_infras))
            if pos_infra:
                vals.update({
                    'customer_ip': pos_infra[0]['customer_ip'],
                    'customer_email': pos_infra[0]['customer_email'],
                    'customer_name': pos_infra[0]['customer_name'],
                    'customer_surname': pos_infra[0]['customer_surname'],
                    'customer_address': pos_infra[0]['customer_address'],
                    'customer_phone': pos_infra[0]['customer_phone'],
                    'customer_id': pos_infra[0]['customer_id'],
                    'customer_identity': pos_infra[0]['customer_identity'],
                    'customer_city': pos_infra[0]['customer_city'],
                    'customer_country': pos_infra[0]['customer_country'],
                    'customer_postal_code': pos_infra[0]['customer_postal_code'],
                    'customer_company': pos_infra[0]['customer_company'],
                    'basket_item_id': pos_infra[0]['basket_item_id'],
                    'basket_item_name': pos_infra[0]['basket_item_name'],
                    'basket_item_desc': pos_infra[0]['basket_item_desc'],
                    'basket_item_categ': pos_infra[0]['basket_item_categ'],
                    'billing_address_contact': pos_infra[0]['billing_address_contact'],
                    'billing_address': pos_infra[0]['billing_address'],
                    'billing_address_city': pos_infra[0]['billing_address_city'],
                    'billing_address_country': pos_infra[0]['billing_address_country'],
                    'shipping_address': pos_infra[0]['shipping_address'],
                    'shipping_address_city': pos_infra[0]['shipping_address_city'],
                    'shipping_address_country': pos_infra[0]['shipping_address_country'],
                    'merchant_active': pos_infra[0]['merchant_active'],
                    'client_active': pos_infra[0]['client_active'],
                    'apikey_active': pos_infra[0]['apikey_active'],
                    'terminal_active': pos_infra[0]['terminal_active'],
                    'username_active': pos_infra[0]['username_active'],
                    'password_active': pos_infra[0]['password_active'],
                    'rfnd_username_active': pos_infra[0]['rfnd_username_active'],
                    'rfnd_password_active': pos_infra[0]['rfnd_password_active'],
                })

            provider_table.create(vals)
        return {item['res_id']: item['id'] for item in provider_table.search_read([], ['id', 'res_id'])}

    def _paylox_api_create_application(self, pos):
        application_table = self.env['payment.acquirer.jetcheckout.api.application']
        domain = [('user_id', '=', self.jetcheckout_user_id)]
        if pos:
            domain.append(('application_id', '=', self.jetcheckout_api_key))
        apps = self._rpc('jet.application', 'search_read', domain)
        for app in apps:
            application_table.create({
                'acquirer_id': self.id,
                'res_id': app['id'],
                'parent_id': False,
                'name': app['name'],
                'application_id': app['application_id'],
                'secret_key': app['secret_key'],
                'is_active': app['is_active'],
                'first_selection': app['first_selection'],
                'second_selection': app['second_selection'],
                'third_selection': app['third_selection'],
                'virtual_poses': app['virtual_poses'],
                'in_use': app['application_id'] == self.jetcheckout_api_key,
            })
        return {item['res_id']: item['id'] for item in application_table.search_read([], ['id', 'res_id'])}

    def _paylox_api_create_pos(self, poses, apps, providers, currencies):
        pos_ids = [pos['id'] for pos in poses]
        pos_prices = self._rpc('jet.pos.price', 'search_read', [('virtual_pos_id', 'in', pos_ids)], ['id', 'virtual_pos_id', 'excluded_bins', 'card_filters', 'is_active', 'from_date', 'offer_name', 'to_date', 'card_family_names', 'installments', 'currency_id', 'imported'])
        pos_price_ids = [price['id'] for price in pos_prices]
        pos_lines = self._rpc('jet.pos.price.line', 'search_read', [('pos_price_id', 'in', pos_price_ids)], ['id', 'pos_price_id', 'installment_type', 'customer_rate', 'cost_rate', 'is_active', 'plus_installment', 'plus_installment_description', 'fixed_customer_rate', 'margin_rate', 'additional_rate', 'only_fundings_active'])

        bank_model = self.env['payment.acquirer.jetcheckout.api.bank']
        banks = self._rpc('jet.bank', 'search_read', [], ['id', 'name'])
        bank_model.create([{
            'acquirer_id': self.id,
            'res_id': bank['id'],
            'name': bank['name'],
        } for bank in banks])

        family_model = self.env['payment.acquirer.jetcheckout.api.family']
        families = self._rpc('jet.card.family', 'search_read', [], ['id', 'name', 'logo_path'])
        family_model.create([{
            'acquirer_id': self.id,
            'res_id': family['id'],
            'name': family['name'],
            'logo': family['logo_path']
        } for family in families])

        bin_model = self.env['payment.acquirer.jetcheckout.api.excluded']
        bins = self._rpc('jet.bin', 'search_read', [], ['id', 'code', 'bank_code', 'card_type', 'card_family_id', 'mandatory_3d', 'program'])
        bin_model.create([{
            'acquirer_id': self.id,
            'res_id': bin['id'],
            'code': bin['code'],
            'bank_code': bin['bank_code'] and bank_model.search([('res_id', '=', bin['bank_code'][0])], limit=1).id,
            'card_family_id': bin['card_family_id'] and family_model.search([('res_id', '=', bin['card_family_id'][0])], limit=1).id,
            'card_type': bin['card_type'],
            'mandatory_3d': bin['mandatory_3d'],
            'program': bin['program'],
        } for bin in bins])

        for pos in poses:
            self.env['payment.acquirer.jetcheckout.api.pos'].create({
                'acquirer_id': self.id,
                'res_id': pos['id'],
                'name': pos['name'],
                'parent_id': False,
                'payment_org_id': providers[pos['payment_org_id'][0]],
                'is_active': pos['is_active'],
                'is_client_active': pos['is_client_active'],
                'is_merchant_active': pos['is_merchant_active'],
                'is_apikey_active': pos['is_apikey_active'],
                'is_terminal_active': pos['is_terminal_active'],
                'is_username_active': pos['is_username_active'],
                'is_password_active': pos['is_password_active'],
                'is_rfnd_username_active': pos['is_rfnd_username_active'],
                'is_rfnd_password_active': pos['is_rfnd_password_active'],
                'client_id': pos['client_id'],
                'merchant_id': pos['merchant_id'],
                'terminal_id': pos['terminal_id'],
                'api_key': pos['api_key'],
                'secret_key': pos['secret_key'],
                'username': pos['username'],
                'password': pos['password'],
                'rfnd_username': pos['rfnd_username'],
                'rfnd_password': pos['rfnd_password'],
                'priority': pos['priority'],
                'usage_3d': pos['usage_3d'],
                'mode': pos['mode'],
                'notes': pos['notes'],
                'is_physical': pos['is_physical'],
                'rates_importable': pos['rates_importable'],
                'import_rates': pos['import_rates'],
                'calc_cust_rates': pos['calc_cust_rates'],
                'customer_ip': pos['customer_ip'],
                'customer_email': pos['customer_email'],
                'customer_name': pos['customer_name'],
                'customer_surname': pos['customer_surname'],
                'customer_address': pos['customer_address'],
                'customer_phone': pos['customer_phone'],
                'customer_id': pos['customer_id'],
                'customer_identity': pos['customer_identity'],
                'customer_city': pos['customer_city'],
                'customer_country': pos['customer_country'],
                'customer_postal_code': pos['customer_postal_code'],
                'customer_company': pos['customer_company'],
                'basket_item_id': pos['basket_item_id'],
                'basket_item_name': pos['basket_item_name'],
                'basket_item_desc': pos['basket_item_desc'],
                'basket_item_categ': pos['basket_item_categ'],
                'billing_address_contact': pos['billing_address_contact'],
                'billing_address': pos['billing_address'],
                'billing_address_city': pos['billing_address_city'],
                'billing_address_country': pos['billing_address_country'],
                'shipping_address': pos['shipping_address'],
                'shipping_address_city': pos['shipping_address_city'],
                'shipping_address_country': pos['shipping_address_country'],
                'applications': [(6, 0, [val for key, val in apps.items() if key in pos['applications']])],
                'excluded_card_families': [(6, 0, family_model.search([('acquirer_id', '=', self.id), ('res_id', 'in', pos['excluded_card_families'])]).ids)],
                'pos_price': [(0, 0, {
                    'acquirer_id': self.id,
                    'res_id': price['id'],
                    'offer_name': price['offer_name'],
                    'currency_id': currencies[price['currency_id'][0]],
                    'is_active': price['is_active'],
                    'from_date': price['from_date'],
                    'to_date': price['to_date'],
                    'card_family_names': price['card_family_names'],
                    'installments': price['installments'],
                    'pos_lines': [(0, 0, {
                        'acquirer_id': self.id,
                        'res_id': line['id'],
                        'installment_type': line['installment_type'],
                        'customer_rate': line['customer_rate'],
                        'cost_rate': line['cost_rate'],
                        'is_active': line['is_active'],
                        'plus_installment': line['plus_installment'],
                        'plus_installment_description': line['plus_installment_description'],
                    }) for line in pos_lines if line['pos_price_id'][0] == price['id']],
                    'card_filters': [(6, 0, family_model.search([('acquirer_id', '=', self.id), ('res_id', 'in', price['card_filters'])]).ids)],
                    'excluded_bins': [(6, 0, bin_model.search([('acquirer_id', '=', self.id), ('res_id', 'in', price['excluded_bins'])]).ids)]
                }) for price in pos_prices if price['virtual_pos_id'][0] == pos['id']],
            })

    def _paylox_api_create(self, poses, pos):
        currencies = self._paylox_api_create_currencies()
        providers = self._paylox_api_create_providers()
        apps = self._paylox_api_create_application(pos)
        self._paylox_api_create_pos(poses, apps, providers, currencies)

    def _paylox_api_read(self):
        data = {}
        data['payment.acquirer.jetcheckout.api.pos'] = {item['id']: item['res_id'] for item in self.env['payment.acquirer.jetcheckout.api.pos'].search_read([('acquirer_id', '=', self.id)], ['id', 'res_id'])}
        data['payment.acquirer.jetcheckout.api.provider'] = {item['id']: item['res_id'] for item in self.env['payment.acquirer.jetcheckout.api.provider'].search_read([('acquirer_id', '=', self.id)], ['id', 'res_id'])}
        data['payment.acquirer.jetcheckout.api.application'] = {item['id']: item['res_id'] for item in self.env['payment.acquirer.jetcheckout.api.application'].search_read([('acquirer_id', '=', self.id)], ['id', 'res_id'])}
        data['payment.acquirer.jetcheckout.api.campaign'] = {item['id']: item['res_id'] for item in self.env['payment.acquirer.jetcheckout.api.campaign'].search_read([('acquirer_id', '=', self.id)], ['id', 'res_id'])}
        data['payment.acquirer.jetcheckout.api.installment'] = {item['id']: item['res_id'] for item in self.env['payment.acquirer.jetcheckout.api.installment'].search_read([('acquirer_id', '=', self.id)], ['id', 'res_id'])}
        data['payment.acquirer.jetcheckout.api.excluded'] = {item['id']: item['res_id'] for item in self.env['payment.acquirer.jetcheckout.api.excluded'].search_read([('acquirer_id', '=', self.id)], ['id', 'res_id'])}
        data['payment.acquirer.jetcheckout.api.family'] = {item['id']: item['res_id'] for item in self.env['payment.acquirer.jetcheckout.api.family'].search_read([('acquirer_id', '=', self.id)], ['id', 'res_id'])}
        data['payment.acquirer.jetcheckout.api.currency'] = {item['id']: item['res_id'] for item in self.env['payment.acquirer.jetcheckout.api.currency'].search_read([('acquirer_id', '=', self.id)], ['id', 'res_id'])}
        data['acquirer'] = self
        return data

    def _paylox_api_sync_campaign(self, poses=None):
        if not poses:
            poses = self.env['payment.acquirer.jetcheckout.api.application'].search([
                ('application_id', '=', self.jetcheckout_api_key)
            ], limit=1).mapped('virtual_pos_ids')
            if not poses:
                return

        api_campaigns_list = poses.filtered(lambda x: x.is_active).mapped('pos_price').filtered(lambda x: x.is_active).mapped('offer_name')
        acq_campaigns_list = self.paylox_campaign_ids.mapped('name')
        api_campaigns = set(api_campaigns_list)
        acq_campaigns = set(acq_campaigns_list)
        creates = []
        unlinks = []

        for campaign in acq_campaigns:
            if campaign not in api_campaigns:
                unlinks.append(campaign)

        for campaign in api_campaigns:
            if campaign not in acq_campaigns:
                creates.append(campaign)

        self.env['payment.acquirer.jetcheckout.campaign'].sudo().search([
            ('acquirer_id', '=', self.id),
            ('name', 'in', unlinks)
        ]).unlink()
        self.env['payment.acquirer.jetcheckout.campaign'].sudo().create([{
            'acquirer_id': self.id,
            'name': name,
        } for name in creates])

    def _paylox_api_upload_vals(self, vals, data, table):
        values = {}
        fields = table._fields.values()
        for field in fields:
            if field.name in vals:
                if field.type == 'one2many':
                    val_list = []
                    for val in vals[field.name]:
                        if val[0] == 0:
                            v = self._paylox_api_upload_vals(val[2], data, self.env[field.comodel_name])
                            val_list.append([0, 0, v])
                        elif val[0] == 1:
                            i = data[field.comodel_name][val[1]]
                            v = self._paylox_api_upload_vals(val[2], data, self.env[field.comodel_name])
                            val_list.append([1, i, v])
                        elif val[0] == 2:
                            i = data[field.comodel_name][val[1]]
                            val_list.append([2, i, 0])
                    values.update({field.name: val_list})
                elif field.type == 'many2one':
                    values.update({field.name: data[field.comodel_name][vals[field.name]]})
                elif field.type == 'many2many':
                    ids = vals[field.name][0][2]
                    values.update({field.name: [[6, 0, [data[field.comodel_name][id] for id in ids]]]})
                else:
                    values.update({field.name: vals[field.name]})
        return values

    def _paylox_api_upload(self, vals, data, table):
        vals = self._paylox_api_upload_vals(vals, data, table)
        fields = table._fields.values()
        for field in fields:
            if field.name in vals:
                if field.type == 'one2many':
                    name = self.env[field.comodel_name]._remote_name
                    for val in vals[field.name]:
                        if val[0] == 0:
                            self._rpc(name, 'create', val[2])
                        elif val[0] == 1:
                            self._rpc(name, 'write', val[1], val[2])
                        elif val[0] == 2:
                            self._rpc(name, 'unlink', val[1])

    def _paylox_api_connect(self, pos=None):
        # Get all data
        domain = [('user_id', '=', self.jetcheckout_user_id)]
        if pos:
            domain.append(('applications.application_id', '=', self.jetcheckout_api_key))
        poses = self._rpc('jet.virtual.pos', 'search_read', domain)

        # Vacuum old data
        self._paylox_api_vacuum()

        # Create transient records
        self._paylox_api_create(poses, pos)
