# -*- coding: utf-8 -*-

def migrate(cr, version):
    cr.execute("UPDATE website SET show_privacy_policy = TRUE, show_sale_agreement = TRUE, show_membership_agreement = TRUE, show_contact_page = TRUE")
