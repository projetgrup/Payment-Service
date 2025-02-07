# -*- coding: utf-8 -*-
from odoo import fields, models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    jetcheckout_api_ok = fields.Boolean('API Active', readonly=True, copy=False)
    jetcheckout_api_contact = fields.Char('API Contact', readonly=True)
    jetcheckout_api_order = fields.Char('API Order', readonly=True)
    jetcheckout_api_product = fields.Char('API Product', readonly=True)
    jetcheckout_api_hash = fields.Char('API Hash', readonly=True)
    jetcheckout_api_id = fields.Char('API TransactionID', readonly=True)
    jetcheckout_api_method = fields.Selection([
        ('card', 'Credit Card'),
        ('bank', 'Bank Transfer'),
        ('credit', 'Shopping Credit'),
    ], string='API Method', readonly=True)
    jetcheckout_api_html = fields.Html('API HTML', sanitize=False, readonly=True)
    jetcheckout_api_card_return_url = fields.Char('API Card Return URL', readonly=True)
    jetcheckout_api_card_result_url = fields.Char('API Card Result URL', readonly=True)
    jetcheckout_api_card_redirect_url = fields.Char('API Card Redirect URL', readonly=True)
    jetcheckout_api_bank_return_url = fields.Char('API Bank Return URL', readonly=True)
    jetcheckout_api_bank_webhook_url = fields.Char('API Bank Webhook URL', readonly=True)
    jetcheckout_api_credit_return_url = fields.Char('API Credit Return URL', readonly=True)
    jetcheckout_api_credit_result_url = fields.Char('API Credit Result URL', readonly=True)

    def write(self, values):
        if 'jetcheckout_payment_ok' in values and any(tx.jetcheckout_api_ok for tx in self):
            values['jetcheckout_payment_ok'] = False
        return super().write(values)
