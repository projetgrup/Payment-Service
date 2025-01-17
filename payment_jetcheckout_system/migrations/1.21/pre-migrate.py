# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists

def migrate(cr, version):
    if not column_exists(cr, 'website', 'show_privacy_policy'):
        cr.execute('ALTER TABLE website ADD COLUMN show_privacy_policy boolean')
    if not column_exists(cr, 'website', 'show_sale_agreement'):
        cr.execute('ALTER TABLE website ADD COLUMN show_sale_agreement boolean')
    if not column_exists(cr, 'website', 'show_membership_agreement'):
        cr.execute('ALTER TABLE website ADD COLUMN show_membership_agreement boolean')
    if not column_exists(cr, 'website', 'show_contact_page'):
        cr.execute('ALTER TABLE website ADD COLUMN show_contact_page boolean')
