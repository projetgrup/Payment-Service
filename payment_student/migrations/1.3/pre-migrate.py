# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists


def migrate(cr, version):
    if not column_exists(cr, 'res_partner', 'system_student_campus_id'):
        cr.execute('ALTER TABLE res_partner ADD COLUMN system_student_campus_id integer')
