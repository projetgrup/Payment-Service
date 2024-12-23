# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists

def migrate(cr, version):
    if not column_exists(cr, 'res_company', 'payment_page_item_expire_ok'):
        cr.execute('ALTER TABLE res_company ADD COLUMN payment_page_item_expire_ok boolean')
    if not column_exists(cr, 'res_company', 'payment_page_item_expire_value'):
        cr.execute('ALTER TABLE res_company ADD COLUMN payment_page_item_expire_value integer')
    if not column_exists(cr, 'res_company', 'payment_page_item_expire_period'):
        cr.execute('ALTER TABLE res_company ADD COLUMN payment_page_item_expire_period varchar')
