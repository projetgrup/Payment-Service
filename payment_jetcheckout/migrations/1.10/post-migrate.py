# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists

def migrate(cr, version):
    if column_exists(cr, "payment_transaction", "jetcheckout_card_program"):
        cr.execute("UPDATE payment_transaction SET jetcheckout_card_program = jetcheckout_card_type")
        cr.execute("UPDATE payment_transaction SET jetcheckout_card_type = NULL")
    if column_exists(cr, "payment_token", "jetcheckout_program"):
        cr.execute("UPDATE payment_token SET jetcheckout_program = jetcheckout_type")
        cr.execute("UPDATE payment_token SET jetcheckout_type = NULL")
