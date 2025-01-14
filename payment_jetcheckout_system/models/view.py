# -*- coding: utf-8 -*-
import uuid
from odoo import models, fields, api, _


class PaymentView(models.Model):
    _name = 'payment.view'
    _inherits = {'ir.ui.view': 'view_id'}
    _description = 'Payment Views'

    view_id = fields.Many2one('ir.ui.view', 'View', auto_join=True, index=True, ondelete='cascade', required=True)
    company_id = fields.Many2one('res.company', ondelete='cascade', default=lambda self: self.env.company)
    uid = fields.Char(string='Access Token', default=lambda self: str(uuid.uuid4()), readonly=True)
    page_id = fields.Many2one('payment.page')
    name = fields.Char(string='Name')
    system = fields.Selection([])
    arch_js = fields.Text()
    arch_css = fields.Text()
