# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.misc import formatLang


class PaymentAcquirerPayloxReport(models.Model):
    _name = 'payment.acquirer.jetcheckout.report'
    _description = 'Paylox Reports'
    _order = 'sequence, id desc'

    @api.depends('acquirer_id.company_id')
    def _compute_company_id(self):
        for report in self:
            report.company_id = report.acquirer_id.company_id.id or self.env.company.id

    name = fields.Char(required=True)
    type = fields.Selection([
        ('receipt', 'Receipt'),
        ('conveyance', 'Conveyance'),
    ], default='receipt')
    version = fields.Char()
    body = fields.Html(sanitize=False)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    acquirer_id = fields.Many2one('payment.acquirer', required=True, domain='[("provider", "=", "jetcheckout")]')
    company_id = fields.Many2one('res.company', compute='_compute_company_id', store=True, readonly=False)

    def render(self, tx):
        res = self.body \
            .replace('{{amount_paid}}', formatLang(self.env, tx.amount, currency_obj=tx.currency_id)) \
            .replace('{{amount_payment}}', formatLang(self.env, tx.jetcheckout_payment_amount, currency_obj=tx.currency_id)) \
            .replace('{{amount_commission}}', formatLang(self.env, tx.jetcheckout_customer_amount, currency_obj=tx.currency_id)) \
            .replace('{{partner_name}}', tx.partner_name) \
            .replace('{{payment_date}}', tx.create_date.strftime('%d/%m/%Y')) \
            .replace('{{card_holder}}', tx.jetcheckout_card_name)
        return res
