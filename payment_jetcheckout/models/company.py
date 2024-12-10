# -*- coding: utf-8 -*-
from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    payment_page_campaign_table_ok = fields.Boolean('Campaign Table on Payment Page')
    payment_page_campaign_table_transpose = fields.Boolean('Transpose Campaign Table on Payment Page')
    payment_page_campaign_table_ids = fields.Many2many('payment.acquirer.jetcheckout.campaign', 'company_campaign_table_rel', 'company_id', 'campaign_id', string='Campaigns on Campaign Table on Payment Page')
    payment_page_campaign_table_included = fields.Boolean(string='Campaigns on Campaign Table Included on Payment Page')
    payment_page_token_wo_commission = fields.Boolean(string='Payment Token Page Amount Without Commission')
