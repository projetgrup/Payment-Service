# -*- coding: utf-8 -*-
from odoo import models, fields


class Website(models.Model):
    _inherit = 'website'

    payment_footer = fields.Html('Footer', sanitize=False)
    payment_privacy_policy = fields.Html('Privacy Policy', sanitize=False)
    payment_sale_agreement = fields.Html('Sale Agreement', sanitize=False)
    payment_membership_agreement = fields.Html('Membership Agreement', sanitize=False)
    payment_contact_page = fields.Html('Contact Page', sanitize=False)
    show_privacy_policy = fields.Boolean('Show Privacy Policy', default=True)
    show_sale_agreement = fields.Boolean('Show Sale Agreement', default=True)
    show_membership_agreement = fields.Boolean('Show Membership Agreement', default=True)
    show_contact_page = fields.Boolean('Show Contact Page', default=True)
