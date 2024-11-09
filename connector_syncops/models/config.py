# -*- coding: utf-8 -*-
from odoo import models, fields

DAYS = {'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3, 'FR': 4, 'SA': 5, 'SU': 6}

class SyncopsSettingsDay(models.Model):
    _name = 'syncops.settings.day'
    _description = 'syncOPS Settings Days'

    name = fields.Char(translate=True, required=True)
    code = fields.Char(required=True)


class SyncopsSettingsNotifType(models.Model):
    _name = 'syncops.settings.notif.type'
    _description = 'syncOPS Settings Notification Types'

    name = fields.Char(translate=True, required=True)
    code = fields.Char(required=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    syncops_url = fields.Char(string='syncOPS Endpoint URL', config_parameter='syncops.url')
