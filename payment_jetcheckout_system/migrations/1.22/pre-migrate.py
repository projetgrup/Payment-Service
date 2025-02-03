# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists

def migrate(cr, version):
    if not column_exists(cr, 'res_partner', 'should_send_email'):
        cr.execute('ALTER TABLE res_partner ADD COLUMN should_send_email boolean')
    if not column_exists(cr, 'res_partner', 'should_send_sms'):
        cr.execute('ALTER TABLE res_partner ADD COLUMN should_send_sms boolean')
