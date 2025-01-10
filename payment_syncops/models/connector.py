# -*- coding: utf-8 -*-
from odoo import models, fields


class SyncopsConnectorHook(models.Model):
    _inherit = 'syncops.connector.hook'

    type = fields.Selection(selection_add=[('partner', 'Partner'), ('item', 'Payment')])
    subtype = fields.Selection(selection_add=[('balance', 'Current Balances'), ('invoice', 'Unpaid Invoices')])