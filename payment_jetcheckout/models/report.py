# -*- coding: utf-8 -*-
from odoo import models, fields, api

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

    def render(self):
        res = self.body \
            .replace('{{var}}', '')
        return res
