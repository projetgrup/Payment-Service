# -*- coding: utf-8 -*-
import requests
import logging
import json
import pytz

from urllib.parse import urlparse
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.http import request
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, DEFAULT_SERVER_DATETIME_FORMAT as DTF

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _compute_is_paylox(self):
        for tx in self:
            tx.is_paylox = tx.acquirer_id.provider == 'jetcheckout'

    def _calc_installment_description_long(self):
        for tx in self:
            desc = tx.jetcheckout_installment_description
            desc_long = ''
            try:
                installment = int(desc)
                if installment == 0:
                    desc_long = ''
                elif installment == 1 and tx.jetcheckout_payment_type in ('virtual_pos', 'physical_pos', 'soft_pos'):
                    desc_long = _('Single payment')
                else:
                    desc_long = _('%s installment') % desc
            except:
                desc_long = desc
            tx.jetcheckout_installment_description_long = desc_long

    @api.depends('jetcheckout_payment_amount', 'jetcheckout_customer_amount', 'jetcheckout_commission_amount')
    def _compute_amounts(self):
        for tx in self:
            tx.jetcheckout_payment_paid = tx.jetcheckout_payment_amount + tx.jetcheckout_customer_amount
            tx.jetcheckout_payment_net = tx.jetcheckout_payment_paid - tx.jetcheckout_commission_amount
            tx.jetcheckout_fund_amount = tx.jetcheckout_payment_amount - tx.jetcheckout_payment_net
            tx.jetcheckout_fund_rate = 100 * tx.jetcheckout_fund_amount / tx.jetcheckout_payment_amount if tx.jetcheckout_payment_amount != 0 else 0

    @api.model
    def _get_default_partner_country_id(self):
        country = self.env.company.country_id
        if not country:
            raise ValidationError(_('Please define a country for this company'))
        return country.id

    partner_vat = fields.Char(string='VAT')
    state = fields.Selection(selection_add=[('expired', 'Expired')], ondelete={'expired': lambda recs: recs.write({'state': 'cancel'})})
    is_paylox = fields.Boolean(compute='_compute_is_paylox')
    jetcheckout_campaign_name = fields.Char('Campaign Name', readonly=True, copy=False)
    jetcheckout_card_name = fields.Char('Card Holder Name', readonly=True, copy=False)
    jetcheckout_card_number = fields.Char('Card Number', readonly=True, copy=False)
    jetcheckout_card_type = fields.Char('Card Type', readonly=True, copy=False)
    jetcheckout_card_family = fields.Char('Card Family', readonly=True, copy=False)
    jetcheckout_vpos_id = fields.Integer('Virtual PoS Id', readonly=True, copy=False)
    jetcheckout_vpos_name = fields.Char('Virtual PoS', readonly=True, copy=False)
    jetcheckout_vpos_ref = fields.Char('Virtual PoS Reference', readonly=True, copy=False)
    jetcheckout_vpos_code = fields.Char('Virtual PoS Code', readonly=True, copy=False)
    jetcheckout_order_id = fields.Char('Order', readonly=True, copy=False)
    jetcheckout_ip_address = fields.Char('IP Address', readonly=True, copy=False)
    jetcheckout_url_address = fields.Char('URL Address', readonly=True, copy=False)
    jetcheckout_transaction_id = fields.Char('Transaction', readonly=True, copy=False)
    jetcheckout_preauth = fields.Boolean('Pre-Authorization', readonly=True, copy=False)
    jetcheckout_postauth = fields.Boolean('Post-Authorization', readonly=True, copy=False)

    jetcheckout_payment_type = fields.Selection(selection=[
        ('virtual_pos', 'Virtual PoS'),
        ('physical_pos', 'Physical PoS'),
        ('soft_pos', 'Soft PoS'),
        ('transfer', 'Wire Transfer'),
        ('wallet', 'Wallet'),
        ('credit', 'Shopping Credit'),
    ], string='Paylox Payment Type', default='virtual_pos', readonly=True, copy=False)
    jetcheckout_payment_type_transfer_service_name = fields.Char('Paylox Payment Type Transfer Service Name', readonly=True, copy=False)
    jetcheckout_payment_type_wallet_service_name = fields.Char('Paylox Payment Type Wallet Service Name', readonly=True, copy=False)
    jetcheckout_payment_type_wallet_id = fields.Integer('Paylox Payment Type Wallet ID', readonly=True, copy=False)
    jetcheckout_payment_type_credit_bank_code = fields.Char('Paylox Payment Type Credit Bank Code', readonly=True, copy=False)
    jetcheckout_payment_ok = fields.Boolean('Payment Required', readonly=True, copy=False, default=True)
    jetcheckout_payment_amount = fields.Monetary('Amount to Pay', readonly=True, copy=False)
    jetcheckout_payment_paid = fields.Monetary('Amount Paid', compute='_compute_amounts', readonly=True, copy=False, store=True)
    jetcheckout_payment_net = fields.Monetary('Amount Net', compute='_compute_amounts', readonly=True, copy=False, store=True)

    jetcheckout_service_code = fields.Char('Paylox Service Code', readonly=True, copy=False)
    jetcheckout_service_message = fields.Char('Paylox Service Message', readonly=True, copy=False)
    jetcheckout_service_suggestion = fields.Char('Paylox Service Suggestion', readonly=True, copy=False)

    jetcheckout_installment_count = fields.Integer('Installment Count', readonly=True, copy=False)
    jetcheckout_installment_plus = fields.Integer('Plus Installment Count', readonly=True, copy=False)
    jetcheckout_installment_description = fields.Char('Installment Description', readonly=True, copy=False)
    jetcheckout_installment_description_long = fields.Char('Installment Long Description', readonly=True, compute='_calc_installment_description_long')
    jetcheckout_installment_amount = fields.Monetary('Installment Amount', readonly=True, copy=False)

    jetcheckout_commission_rate = fields.Float('Cost Rate', digits=(12,4), readonly=True, copy=False)
    jetcheckout_commission_amount = fields.Monetary('Cost Amount', readonly=True, copy=False)
    jetcheckout_customer_rate = fields.Float('Customer Rate', digits=(12,4), readonly=True, copy=False)
    jetcheckout_customer_amount = fields.Monetary('Customer Amount', readonly=True, copy=False)
    jetcheckout_fund_rate = fields.Float('Fund Rate', digits=(12,4), compute='_compute_amounts', readonly=True, copy=False, store=True)
    jetcheckout_fund_amount = fields.Monetary('Fund Amount', compute='_compute_amounts', readonly=True, copy=False, store=True)
    jetcheckout_website_id = fields.Many2one('website', 'Website', readonly=True, copy=False)
    jetcheckout_date_expiration = fields.Datetime('Expiration Date', readonly=True, copy=False)

    paylox_product_ids = fields.One2many('payment.transaction.product', 'transaction_id', 'Products')

    @api.model
    def _compute_reference(self, provider, prefix=None, separator='-', **kwargs):
        if provider == 'jetcheckout':
            sequence = 'payment.jetcheckout.transaction'
            reference = self.env['ir.sequence'].sudo().next_by_code(sequence)
            if not reference:
                raise ValidationError(_('You have to define a sequence for %s') % sequence)
            return reference
        return super()._compute_reference(provider, prefix=prefix, separator=separator, **kwargs) 

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if 'partner_vat' not in values:
                partner = self.env['res.partner'].browse(values['partner_id'])
                values.update({'partner_vat': partner.vat})

        txs = super().create(values_list)

        for tx in txs:
            partner_phone = tx.partner_id.mobile or tx.partner_id.phone
            if partner_phone:
                tx.write({'partner_phone': partner_phone})
        return txs

    def unlink(self):
        for tx in self:
            if tx.state not in ('draft', 'pending'):
                raise ValidationError(_('Only "Draft" or "Pending" payment transactions can be removed'))
        return super().unlink()

    def _paylox_api_status(self):
        url = '%s/api/v1/payment/status' % self.acquirer_id._get_paylox_api_url()
        data = {
            "application_key": self.acquirer_id.jetcheckout_api_key,
            "order_id": self.jetcheckout_order_id,
            "lang": "tr",
        }

        response = requests.post(url, data=json.dumps(data))
        if response.status_code == 200:
            result = response.json()
            if result['response_code'] == "00200":
                values = {'result': result}
            else:
                values = {'error': _('%s (Error Code: %s)') % (result['message'], result['response_code'])}
        else:
            values = {'error': _('%s (Error Code: %s)') % (response.reason, response.status_code)}
        return values

    def _paylox_payment(self, values={}, raise_exception=False):
        if self.payment_id:
            return False

        if not self.jetcheckout_payment_ok:
            self.write({'jetcheckout_payment_ok': True})

        vpos_name = self.jetcheckout_vpos_name
        vpos_ref = self.jetcheckout_vpos_ref
        if self.jetcheckout_payment_type == 'credit' and self.jetcheckout_payment_type_credit_bank_code:
            vpos_ref = self.jetcheckout_payment_type_credit_bank_code
        line = self.env.context.get('journal_line') or self.acquirer_id.sudo()._get_journal_line(vpos_name, vpos_ref)
        if not line:
            message = _('There is no journal line for %s in %s (%s)') % (vpos_name, self.acquirer_id.name, self.reference)
            if raise_exception:
                raise ValidationError(message)
            self.write({'state_message': message})
            return False

        if not line.journal_id:
            message = _('There is no journal for %s in %s (%s)') % (vpos_name, self.acquirer_id.name, self.reference)
            if raise_exception:
                raise ValidationError(message)
            self.write({'state_message': message})
            return False

        payment_method = self.env.ref('payment_jetcheckout.payment_method_jetcheckout')
        payment_method_line = line.journal_id.inbound_payment_method_line_ids.filtered(lambda x: x.payment_method_id.id == payment_method.id)
        if not payment_method_line:
            message = _('Paylox payment method has not been set yet on inbound payment methods of journal %s.' % line.journal_id.name)
            if raise_exception:
                raise ValidationError(message)
            self.write({'state_message': message})
            return False

        payment = self.env['account.payment'].with_context(line=line, skip_account_move_synchronization=True).create({
            'date': self.create_date.date(),
            'amount': abs(self.amount),
            'payment_type': 'outbound' if self.source_transaction_id else 'inbound',
            'partner_id': self.partner_id.commercial_partner_id.id,
            'journal_id': line.journal_id.id,
            'payment_method_line_id': payment_method_line.id,
            'payment_token_id': self.token_id.id,
            'payment_transaction_id': self.id,
            'ref': self.reference,
            **values
        })
        self.write({'payment_id': payment.id})

        if not self.env.context.get('post_later'):
            payment._paylox_post(line, self.jetcheckout_customer_amount, self.jetcheckout_ip_address)
        return payment

    def _paylox_refund_postprocess_values(self, amount=0):
        return {
            'jetcheckout_card_name': self.jetcheckout_card_name,
            'jetcheckout_card_number': self.jetcheckout_card_number,
            'jetcheckout_card_type': self.jetcheckout_card_type,
            'jetcheckout_card_family': self.jetcheckout_card_family,
            'jetcheckout_vpos_id': self.jetcheckout_vpos_id,
            'jetcheckout_vpos_name': self.jetcheckout_vpos_name,
            'jetcheckout_vpos_ref': self.jetcheckout_vpos_ref,
            'jetcheckout_commission_rate': self.jetcheckout_commission_rate,
            'jetcheckout_commission_amount': -self.jetcheckout_commission_amount * amount / self.amount if self.amount else 0,
            'jetcheckout_customer_rate': self.jetcheckout_customer_rate,
            'jetcheckout_customer_amount': -self.jetcheckout_customer_amount * amount / self.amount if self.amount else 0,
            'is_post_processed': True,
            'state': 'done',
            'state_message': _('Transaction has been refunded successfully.'),
            'last_state_change': fields.Datetime.now(),
        }

    def _paylox_refund_postprocess(self, amount=0):
        tx = self._create_refund_transaction(amount_to_refund=amount, **self._paylox_refund_postprocess_values(amount=amount))
        if not self.env.context.get('skip_payment'):
            tx.paylox_payment()
        tx._log_sent_message()
        return tx

    def _paylox_api_refund(self, amount=0.0, **kwargs):
        self.ensure_one()
        url = '%s/api/v1/payment/refund' % self.acquirer_id._get_paylox_api_url()
        data = {
            "application_key": self.acquirer_id.jetcheckout_api_key,
            "order_id": self.jetcheckout_order_id,
            "transaction_id": self.jetcheckout_transaction_id,
            "amount": round(amount * 100),
            "currency": self.currency_id.name,
            "language": "tr",
        }

        response = requests.post(url, data=json.dumps(data))
        if response.status_code == 200:
            result = response.json()
            if result['response_code'] == "00":
                values = {'result': result}
            else:
                values = {'error': _('%s (Error Code: %s)') % (result['message'], result['response_code'])}
        else:
            values = {'error': _('%s (Error Code: %s)') % (response.reason, response.status_code)}

        if 'error' in values:
            raise UserError(values['error'])
        return self._paylox_refund_postprocess(amount)

    def _paylox_api_cancel(self, **kwargs):
        self.ensure_one()
        if self.state == 'cancel':
            return {}

        url = '%s/api/v1/payment/cancel' % self.acquirer_id._get_paylox_api_url()
        data = {
            "application_key": self.acquirer_id.jetcheckout_api_key,
            "order_id": self.jetcheckout_order_id,
            "transaction_id": self.jetcheckout_transaction_id,
            "language": "tr",
        }

        response = requests.post(url, data=json.dumps(data))
        if response.status_code == 200:
            result = response.json()
            if result['response_code'] in ("00", "01"):
                values = {'result': result}
            else:
                values = {'error': _('%s (Error Code: %s)') % (result['message'], result['response_code'])}
        else:
            values = {'error': _('%s (Error Code: %s)') % (response.reason, response.status_code)}
        return values

    def _paylox_auth_postprocess_values(self):
        return {
            'state': 'authorized',
            'is_post_processed': True,
            'last_state_change': fields.Datetime.now(),
            'state_message': _('Payment has been held on pre-authorization.'),
        }

    def _paylox_auth_postprocess(self):
        if not self.state == 'auth':
            self.write(self._paylox_auth_postprocess_values())
        self.paylox_verify_token()

    def _paylox_done_postprocess_values(self):
        return {
            'state': 'done',
            'is_post_processed': True,
            'last_state_change': fields.Datetime.now(),
            'state_message': _('Transaction is successful.'),
        }

    def _paylox_done_postprocess(self):
        if not self.state == 'done':
            self.write(self._paylox_done_postprocess_values())
        self.paylox_verify_token()
        self.paylox_order_confirm()
        self.paylox_payment()

    def _send_capture_request(self):
        super()._send_capture_request()
        if self.provider != 'jetcheckout':
            return

        amount = self.env.context.get('amount', self.amount)
        url = '%s/api/v1/payment/postauth' % self.acquirer_id._get_paylox_api_url()
        data = {
            "application_key": self.acquirer_id.jetcheckout_api_key,
            "transaction_id": self.jetcheckout_transaction_id,
            "ip_address": request.httprequest.remote_addr,
            "amount": int(amount * 100),
            "language": "tr",
        }

        response = requests.post(url, data=json.dumps(data))
        if response.status_code == 200:
            result = response.json()
            if result['response_code'] == "00":
                self.jetcheckout_postauth = True
                self._paylox_done_postprocess()
            else:
                raise UserError(_('%s (Error Code: %s)') % (result['message'], result['response_code']))
        else:
            raise UserError(_('%s (Error Code: %s)') % (response.reason, response.status_code))

    def paylox_verify_token(self):
        try:
            if self.token_id and not self.token_id.verified:
                self.token_id.verified = True
        except:
            pass

    def paylox_order_confirm(self):
        self.ensure_one()
        orders = hasattr(self, 'sale_order_ids') and self.sale_order_ids.filtered(lambda x: x.state not in ('sale','done'))
        if not orders:
            return

        try:
            self.env.cr.commit()
            commission = self.jetcheckout_customer_amount
            if commission > 0:
                product = self.env.ref('payment_jetcheckout.product_commission')
                orders[0].write({
                    'order_line': [(0, 0, {
                        'product_id': product.id,
                        'price_unit': commission,
                    })]
                })
            orders.with_context(send_email=True).action_confirm()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error('Confirming order for transaction %s is failed\n%s' % (self.reference, e))

    def action_payment(self):
        for tx in self:
            tx.paylox_payment()

    def paylox_payment(self):
        self.ensure_one()
        if not self.jetcheckout_payment_ok:
            return

        try:
            self.env.cr.commit()
            payment = self.sudo()._paylox_payment()
            if payment:
                if self.invoice_ids:
                    self.invoice_ids.filtered(lambda inv: inv.state == 'draft').action_post()
                    (payment.line_ids + self.invoice_ids.line_ids).filtered(lambda line: line.account_id == payment.destination_account_id and not line.reconciled).reconcile()
                self.write({
                    'state_message': _('Transaction is succesful and payment has been validated.'),
                })
            else:
                if not self.state_message:
                    self.write({
                        'state_message': _('Transaction is succesful.'),
                    })
        except Exception as e:
            self.env.cr.rollback()
            self.write({
                'state_message': _('Transaction is succesful, but payment could not be validated. Probably one of partner or journal accounts are missing.') + '\n' + str(e),
            })
            _logger.warning('Creating payment for transaction %s is failed\n%s' % (self.reference, e))

    def _paylox_cancel_postprocess_values(self):
        return {
            'state': 'cancel',
            'state_message': _('Transaction has been cancelled successfully.'),
            'last_state_change': fields.Datetime.now(),
        }

    def _paylox_cancel_postprocess(self):
        if not self.state == 'cancel':
            self.write(self._paylox_cancel_postprocess_values())
        if self.payment_id:
            self.payment_id.action_draft()
            self.payment_id.unlink()

    def _paylox_cancel(self):
        self.ensure_one()

        offset = relativedelta(hours=3) # Turkiye Timezone
        expired = (self.create_date + offset).date() + relativedelta(days=1)
        today = (datetime.now() + offset).date()
        if today >= expired:
            raise UserError(_('Cancellation period seems expired. Please consider refunding the transaction.'))

        if not self.state == 'cancel':
            if not self.state in ('draft', 'pending'):
                values = self._paylox_api_cancel()
                if 'error' in values:
                    raise UserError(values['error'])
            self._paylox_cancel_postprocess()

    def paylox_cancel(self):
        self.ensure_one()
        if not self.env.user.has_group('payment_jetcheckout.group_transaction_cancel'):
            raise AccessError(_('You do not have any permission to cancel this transaction'))
 
        self._paylox_cancel()

    def _paylox_refund(self, amount):
        self.ensure_one()
        if amount > self.amount:
            raise UserError(_('Refund amount cannot be higher than total amount'))
        return self._paylox_api_refund(amount)

    def paylox_refund(self):
        self.ensure_one()
        if not self.env.user.has_group('payment_jetcheckout.group_transaction_refund'):
            raise AccessError(_('You do not have any permission to refund this transaction'))

        refunds = self.search([('source_transaction_id', '=', self.id)])
        vals = {
            'transaction_id': self.id,
            'total': self.amount + sum(refunds.mapped('amount')),
            'currency_id': self.currency_id.id,
        }
        refund = self.env['payment.acquirer.jetcheckout.refund'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.acquirer.jetcheckout.refund',
            'res_id': refund.id,
            'name': _('Create refund for %s') % self.reference,
            'view_mode': 'form',
            'target': 'new',
        }

    def _paylox_process_query(self, values):
        if 'commission_amount' not in values:
            values['commission_amount'] = float_round(self.amount * values['commission_rate'] / 100, 2)

        vpos_id = values.get('vpos_id', 0)
        vpos_name = values.get('vpos_name', '')
        amount = values.get('amount', self.amount)
        commission = values.get('commission_amount', 0)

        self.write({
            'amount': amount,
            'fees': commission,
            'jetcheckout_vpos_id': vpos_id,
            'jetcheckout_vpos_name': vpos_name,
            'jetcheckout_vpos_ref': values.get('vpos_ref', ''),
            'jetcheckout_vpos_ref': values.get('vpos_ref', ''),
            'jetcheckout_vpos_code': values.get('vpos_code', ''),
            'jetcheckout_service_code': values.get('service_code', False),
            'jetcheckout_service_message': values.get('service_message', False),
            'jetcheckout_commission_rate': values.get('commission_rate', 0),
            'jetcheckout_commission_amount': values.get('commission_amount', 0),
            'jetcheckout_card_type': values.get('card_program', self.jetcheckout_card_type),
            'jetcheckout_card_family': values.get('card_family', self.jetcheckout_card_family),
            'jetcheckout_card_number': self.jetcheckout_card_number or '%s**********' % (values.get('bin_code', '') or '',),
            'jetcheckout_payment_amount': self.jetcheckout_payment_amount or amount - self.jetcheckout_customer_amount,
        })

        journal_line = self.env['payment.acquirer.jetcheckout.journal'].sudo().search([('res_id', '=', vpos_id)], limit=1)
        if journal_line and not journal_line.name == vpos_name:
            journal_line.write({'name': vpos_name})

        if values['successful']:
            if 'cancelled' in values and values['cancelled']:
                self._paylox_cancel_postprocess()
            elif 'preauth' in values and values['preauth']:
                if 'postauth' in values and values['postauth']:
                    self.jetcheckout_postauth = True
                    self._paylox_done_postprocess()
                else:
                    self._paylox_auth_postprocess()
            else:
                self._paylox_done_postprocess()
        else:
            if self.state == 'error' or self.env.context.get('skip_error'):
                return
            else:
                self.write({
                    'state': 'error',
                    'state_message': _('%s (Error Code: %s)') % (values.get('message', '-'), values.get('code','')),
                    'jetcheckout_service_suggestion': values.get('service_suggestion') or False,
                    'last_state_change': fields.Datetime.now(),
                })

    def _paylox_query(self, values={}):
        self.ensure_one()
        if not values:
            values = self._paylox_api_status()
            if 'error' in values:
                now = fields.Datetime.now()
                date = now - relativedelta(minutes=10)
                if (date > self.write_date):
                    self.write({
                        'state': 'error',
                        'state_message': values['error'],
                        'last_state_change': now,
                    })
                    self.env.cr.commit()
                raise UserError(values['error'])

            result = values['result']
            commission_rate = result['expected_cost_rate']
            if self.source_transaction_id:
                self.amount = -abs(result.get('amount', self.amount))

            commission_amount = float_round(self.amount * commission_rate / 100, 2)
            values = {
                'date': result['transaction_date'][:19],
                'vpos_id': result['virtual_pos_id'],
                'vpos_name': result['virtual_pos_name'],
                'vpos_ref': result['pos_bank_eft_code'] or result['card_bank_eft_code'],
                'vpos_code': result['auth_code'],
                'successful': result['successful'],
                'completed': result['completed'],
                'cancelled': result['cancelled'],
                'threed': result['is_3d'],
                'auth_code': result['auth_code'],
                'preauth': result['preauth'],
                'postauth': result['postauth'],
                'service_code': result['payment_response_code'],
                'service_message': result['payment_response_message'],
                'card_family': result['card_family'] and result['card_family'].lower().capitalize() or '',
                'card_program': result['card_program'] and result['card_program'].lower().capitalize() or '',
                'bin_code': result['bin_code'],
                'service_ref_id': result['service_ref_id'],
                'commission_amount': commission_amount,
                'commission_rate': commission_rate,
                'customer_amount': self.jetcheckout_customer_amount,
                'customer_rate': self.jetcheckout_customer_rate,
                'currency_id': self.currency_id.id,
                'amount': self.amount,
            }

        self._paylox_process_query(values)
        return values

    def paylox_query(self):
        self.ensure_one()
        if not self.jetcheckout_order_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'payment.acquirer.jetcheckout.prestatus',
                'context': {'default_tx_id': self.id},
                'name': _('%s Transaction Status') % self.reference,
                'view_mode': 'form',
                'target': 'new',
            }

        values = self._paylox_query()
        status = self.env['payment.acquirer.jetcheckout.status'].create(values)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.acquirer.jetcheckout.status',
            'res_id': status.id,
            'name': _('%s Transaction Status') % self.reference,
            'view_mode': 'form',
            'target': 'new',
        }

    def _paylox_expire(self):
        self.filtered(lambda x: x.state in ('draft', 'pending')).write({
            'state': 'expired',
            'state_message': _('Transaction has expired'),
            'last_state_change': fields.Datetime.now(),
        })

    def action_paylox_redirect_transaction(self):
        self.ensure_one()
        acquirer = self.acquirer_id
        result = acquirer._rpc('jet.payment.transaction', 'search_read', [('transaction_id', '=', self.jetcheckout_transaction_id)], ['id'])
        if not result:
            raise UserError(_('This transaction could not be found on payment server'))

        url = urlparse(acquirer.jetcheckout_gateway_app or 'https://jetcheckout.com')
        return {
            'type': 'ir.actions.act_url',
            'url': '%s/web#id=%s&model=jet.payment.transaction&view_type=form' % ('%s://%s' % (url.scheme, url.netloc), result[0]['id']),
            'target': 'new',
        }

    @api.model
    def paylox_expire(self):
        self.sudo().search([
            ('state', 'in', ('draft', 'pending')),
            ('jetcheckout_date_expiration', '!=', False),
            ('jetcheckout_date_expiration', '<', fields.Datetime.now()),
        ])._paylox_expire()

    @api.model
    def paylox_resync_pending(self):
        date = datetime.now() - relativedelta(minutes=30)
        domain = [
            ('state', '=', 'pending'),
            ('source_transaction_id', '=', False),
            ('acquirer_id.provider', '=', 'jetcheckout'),
            ('create_date', '<=', date)
        ]

        txs = self.sudo().search(domain)
        for tx in txs:
            try:
                tx._paylox_query()
                self.env.cr.commit()
            except:
                self.env.cr.rollback()

        refunds = self.sudo().search([('source_transaction_id', 'in', txs.ids)])
        for refund in refunds:
            try:
                ref = refund.source_transaction_id
                refund.write({
                    'jetcheckout_card_name': ref.jetcheckout_card_name,
                    'jetcheckout_card_number': ref.jetcheckout_card_number,
                    'jetcheckout_card_type': ref.jetcheckout_card_type,
                    'jetcheckout_card_family': ref.jetcheckout_card_family,
                    'jetcheckout_vpos_id': ref.jetcheckout_vpos_id,
                    'jetcheckout_vpos_name': ref.jetcheckout_vpos_name,
                    'jetcheckout_vpos_ref': ref.jetcheckout_vpos_ref,
                    'jetcheckout_commission_rate': ref.jetcheckout_commission_rate,
                    'jetcheckout_commission_amount': -ref.jetcheckout_commission_amount * refund.amount / ref.amount if ref.amount else 0,
                })
                self.env.cr.commit()
            except:
                self.env.cr.rollback()

    @api.model
    def paylox_resync(self, date_start=None, date_end=None, companies=None, states=None):
        """
        Use this function in case of emergency when transaction records are corrupted.
        It requests data from payment service and resync related transactions.
        """
        tz = pytz.timezone('Europe/Istanbul')
        offset = tz.utcoffset(fields.Datetime.now())
        if date_start is not False:
            date_start = datetime.strptime(date_start, DF).date() if date_start else date.today() - relativedelta(days=1)
            date_start = datetime.combine(date_start, datetime.min.time()) + offset

        if date_start is not False:
            date_end = datetime.strptime(date_end, DF).date() if date_end else date.today()
            date_end = datetime.combine(date_end, datetime.min.time()) + offset

        domain = [
            ('acquirer_id.provider', '=', 'jetcheckout'),
            ('source_transaction_id', '=', False),
        ]
        if date_start:
            domain.append(('create_date', '>=', date_start.strftime(DTF)))
        if date_end:
            domain.append(('create_date', '<=', date_end.strftime(DTF)))
        if companies:
            domain.append(('company_id', 'in', companies))
        if states:
            domain.append(('state', 'in', states))

        txs = self.sudo().search(domain)
        for tx in txs:
            try:
                tx._jetcheckout_query()
                self.env.cr.commit()
            except:
                self.env.cr.rollback()

        refunds = self.sudo().search([('source_transaction_id', 'in', txs.ids)])
        for refund in refunds:
            try:
                ref = refund.source_transaction_id
                refund.write({
                    'jetcheckout_card_name': ref.jetcheckout_card_name,
                    'jetcheckout_card_number': ref.jetcheckout_card_number,
                    'jetcheckout_card_type': ref.jetcheckout_card_type,
                    'jetcheckout_card_family': ref.jetcheckout_card_family,
                    'jetcheckout_vpos_id': ref.jetcheckout_vpos_id,
                    'jetcheckout_vpos_name': ref.jetcheckout_vpos_name,
                    'jetcheckout_vpos_ref': ref.jetcheckout_vpos_ref,
                    'jetcheckout_commission_rate': ref.jetcheckout_commission_rate,
                    'jetcheckout_commission_amount': -ref.jetcheckout_commission_amount * refund.amount / ref.amount if ref.amount else 0,
                })
                self.env.cr.commit()
            except:
                self.env.cr.rollback()

    #TODO Remove
    @api.model
    def jetcheckout_expire(self):
        self.paylox_expire()

    #TODO Remove
    @api.model
    def jetcheckout_resync(self, date_start=None, date_end=None, companies=None, states=None):
        self.paylox_resync(date_start=date_start, date_end=date_end, companies=companies, states=states)


class PaymentTransactionProduct(models.Model):
    _name = 'payment.transaction.product'
    _description = 'Payment Transaction Product'

    transaction_id = fields.Many2one('payment.transaction', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    uom = fields.Char(related='product_id.uom_id.name')
    name = fields.Char()
    code = fields.Char()
    qty = fields.Float()
    categ = fields.Char()
    brand = fields.Char()
    price = fields.Float()
