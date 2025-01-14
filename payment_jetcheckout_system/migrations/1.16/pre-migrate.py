# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists

def migrate(cr, version):
    if not column_exists(cr, 'res_company', 'payment_dashboard_button_contactless_ok'):
        cr.execute('ALTER TABLE res_company ADD COLUMN payment_dashboard_button_contactless_ok boolean')

    if not column_exists(cr, 'res_company', 'payment_dashboard_button_contactless_url'):
        cr.execute('ALTER TABLE res_company ADD COLUMN payment_dashboard_button_contactless_url varchar')

    if not column_exists(cr, 'res_users', 'payment_contactless_ok'):
        cr.execute('ALTER TABLE res_users ADD COLUMN payment_contactless_ok boolean')

    if not column_exists(cr, 'res_users', 'payment_contactless_ok'):
        cr.execute('ALTER TABLE res_users ADD COLUMN payment_contactless_ok boolean')
