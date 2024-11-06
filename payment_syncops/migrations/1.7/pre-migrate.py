# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists

def migrate(cr, version):
    if not column_exists(cr, 'res_company', 'syncops_sync_item_split'):
        cr.execute('ALTER TABLE res_company ADD COLUMN syncops_sync_item_split boolean')
    if not column_exists(cr, 'res_company', 'syncops_cron_sync_partner_hour'):
        cr.execute('ALTER TABLE res_company ADD COLUMN syncops_cron_sync_partner_hour integer')
    if not column_exists(cr, 'res_company', 'syncops_cron_sync_item_notif_ok'):
        cr.execute('ALTER TABLE res_company ADD COLUMN syncops_cron_sync_item_notif_ok boolean')
    if not column_exists(cr, 'res_company', 'syncops_cron_sync_item_notif_hour'):
        cr.execute('ALTER TABLE res_company ADD COLUMN syncops_cron_sync_item_notif_hour integer')
    if not column_exists(cr, 'res_company', 'syncops_cron_sync_item_notif_tag_ok'):
        cr.execute('ALTER TABLE res_company ADD COLUMN syncops_cron_sync_item_notif_tag_ok boolean')
