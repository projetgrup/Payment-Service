# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists

def migrate(cr, version):
    if column_exists(cr, "payment_transaction", "jetcheckout_card_type_temp"):
        cr.execute("UPDATE payment_transaction SET jetcheckout_card_program = jetcheckout_card_type_temp")
        cr.execute("ALTER TABLE payment_transaction DROP COLUMN jetcheckout_card_type_temp")
    if column_exists(cr, "payment_token", "jetcheckout_type_temp"):
        cr.execute("UPDATE payment_token SET jetcheckout_program = jetcheckout_type_temp")
        cr.execute("ALTER TABLE payment_token DROP COLUMN jetcheckout_type_temp")
