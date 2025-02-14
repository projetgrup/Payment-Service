# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists

def migrate(cr, version):
    if not column_exists(cr, 'res_company', 'payment_token_ok'):
        cr.execute('ALTER TABLE res_company ADD COLUMN payment_token_ok boolean')
    if not column_exists(cr, 'res_company', 'payment_point_ok'):
        cr.execute('ALTER TABLE res_company ADD COLUMN payment_point_ok boolean')
    if not column_exists(cr, 'res_partner', 'paylox_token_ref'):
        cr.execute('ALTER TABLE res_partner ADD COLUMN paylox_token_ref varchar')
