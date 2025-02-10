# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists

def migrate(cr, version):
    if column_exists(cr, "payment_transaction", "jetcheckout_card_type"):
        cr.execute("ALTER TABLE payment_transaction ADD COLUMN jetcheckout_card_type_temp varchar")
        cr.execute("UPDATE payment_transaction SET jetcheckout_card_type_temp = jetcheckout_card_type")
    if column_exists(cr, "payment_token", "jetcheckout_type"):
        cr.execute("ALTER TABLE payment_token ADD COLUMN jetcheckout_type_temp varchar")
        cr.execute("UPDATE payment_token SET jetcheckout_type_temp = jetcheckout_type")
