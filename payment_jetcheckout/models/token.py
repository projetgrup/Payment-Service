# -*- coding: utf-8 -*-
import uuid
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PaymentToken(models.Model):
    _inherit = 'payment.token'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    jetcheckout_ref = fields.Char('Credit Card Token')
    jetcheckout_type = fields.Char('Credit Card Type')
    jetcheckout_program = fields.Char('Credit Card Program')
    jetcheckout_holder = fields.Char('Credit Card Holder')
    jetcheckout_number = fields.Char('Credit Card Number')
    jetcheckout_family = fields.Char('Credit Card Family')
    jetcheckout_expiry = fields.Char('Credit Card Expiry')
    jetcheckout_security = fields.Char('Credit Card Security')
    jetcheckout_limit_card = fields.Float(string='Credit Card Limit')
    jetcheckout_limit_tx = fields.Float(string='Transaction Based Limit')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res['jetcheckout_ref'] = str(uuid.uuid4())
        return res

    def unlink(self):
        for token in self:
            if token.transaction_ids:
                raise UserError(_('Token "%s" cannot be deleted because of it has been used in a transaction.') % token.name)
        return super().unlink()
