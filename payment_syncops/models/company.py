# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    syncops_sync_item_subtype = fields.Char()
    syncops_sync_item_force = fields.Boolean()
    syncops_sync_item_split = fields.Boolean()
    syncops_cron_sync_partner = fields.Boolean()
    syncops_cron_sync_partner_hour = fields.Integer()
    syncops_cron_sync_partner_day_ids = fields.Many2many(
        comodel_name='syncops.settings.day',
        relation='syncops_settings_partner_day_company_rel',
        column1='company_id',
        column2='day_id',
    )
    syncops_cron_sync_item = fields.Boolean()
    syncops_cron_sync_item_hour = fields.Integer()
    syncops_cron_sync_item_day_ids = fields.Many2many(
        comodel_name='syncops.settings.day',
        relation='syncops_settings_item_day_company_rel',
        column1='company_id',
        column2='day_id',
    )
    syncops_cron_sync_item_subtype = fields.Selection([
        ('balance', 'Current Balances'),
        ('invoice', 'Unpaid Invoices'),
    ])
    syncops_cron_sync_item_notif_ok = fields.Boolean()
    syncops_cron_sync_item_notif_hour = fields.Integer()
    syncops_cron_sync_item_notif_type_ids = fields.Many2many(
        comodel_name='syncops.settings.notif.type',
        relation='syncops_settings_item_notif_type_company_rel',
        column1='company_id',
        column2='type_id',
    )
    syncops_cron_sync_item_notif_tag_ok = fields.Boolean()
    syncops_cron_sync_item_notif_tag_ids = fields.Many2many(
        comodel_name='res.partner.category',
        relation='company_syncops_cron_sync_item_notif_tag_rel',
        column1='company_id',
        column2='category_id',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    syncops_check_iban = fields.Boolean()
    syncops_check_card = fields.Boolean()
    syncops_payment_page_partner_required = fields.Boolean()
