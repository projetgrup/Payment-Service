# -*- coding: utf-8 -*-

def migrate(cr, version):
    cr.execute("UPDATE res_partner SET should_send_email = TRUE, should_send_sms = TRUE")
