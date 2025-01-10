# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists

def migrate(cr, version):
    if not column_exists(cr, 'res_partner', 'syncops_data'):
        cr.execute('ALTER TABLE res_partner ADD COLUMN syncops_data text')
