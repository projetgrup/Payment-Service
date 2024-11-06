# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PaymentSettings(models.TransientModel):
    _inherit = 'payment.settings'

    @api.depends('company_id')
    def _compute_syncops_cron_sync_item_notif_tag_opt(self):
        for setting in self:
            setting.syncops_cron_sync_item_notif_tag_opt = 'include' if setting.company_id.syncops_cron_sync_item_notif_tag_ok else 'exclude'

    def _set_syncops_cron_sync_item_notif_tag_opt(self):
        for setting in self:
            setting.company_id.syncops_cron_sync_item_notif_tag_ok = setting.syncops_cron_sync_item_notif_tag_opt == 'include'

    syncops_sync_item_force = fields.Boolean(related='company_id.syncops_sync_item_force', readonly=False)
    syncops_sync_item_split = fields.Boolean(related='company_id.syncops_sync_item_split', readonly=False)
    syncops_cron_sync_partner = fields.Boolean(related='company_id.syncops_cron_sync_partner', readonly=False)
    syncops_cron_sync_partner_hour = fields.Integer(related='company_id.syncops_cron_sync_partner_hour', readonly=False)
    syncops_cron_sync_item = fields.Boolean(related='company_id.syncops_cron_sync_item', readonly=False)
    syncops_cron_sync_item_hour = fields.Integer(related='company_id.syncops_cron_sync_item_hour', readonly=False)
    syncops_cron_sync_item_subtype = fields.Selection(related='company_id.syncops_cron_sync_item_subtype', readonly=False)
    syncops_cron_sync_item_notif_ok = fields.Boolean(related='company_id.syncops_cron_sync_item_notif_ok', readonly=False)
    syncops_cron_sync_item_notif_hour = fields.Integer(related='company_id.syncops_cron_sync_item_notif_hour', readonly=False)
    syncops_cron_sync_item_notif_tag_ok = fields.Boolean(related='company_id.syncops_cron_sync_item_notif_tag_ok', readonly=False)
    syncops_cron_sync_item_notif_tag_ids = fields.Many2many(related='company_id.syncops_cron_sync_item_notif_tag_ids', readonly=False)
    syncops_cron_sync_item_notif_tag_opt = fields.Selection(
        selection=[('include', 'include'), ('exclude', 'exclude')],
        compute='_compute_syncops_cron_sync_item_notif_tag_opt',
        inverse='_set_syncops_cron_sync_item_notif_tag_opt',
        string='syncOPS Cron Sync Item Notification Tag Option'
    )
    syncops_payment_page_partner_required = fields.Boolean(related='company_id.syncops_payment_page_partner_required', readonly=False)
    syncops_check_iban = fields.Boolean(related='company_id.syncops_check_iban', readonly=False)
    syncops_check_card = fields.Boolean(related='company_id.syncops_check_card', readonly=False)

    @api.onchange('syncops_cron_sync_partner_hour')
    def onchange_syncops_cron_sync_partner_hour(self):
        if self.syncops_cron_sync_partner_hour >= 24:
            self.syncops_cron_sync_partner_hour %= 24

    @api.onchange('syncops_cron_sync_item_hour')
    def onchange_syncops_cron_sync_item_hour(self):
        if self.syncops_cron_sync_item_hour >= 24:
            self.syncops_cron_sync_item_hour %= 24
