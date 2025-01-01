# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError



class SmsProvider(models.Model):
    _inherit = 'sms.provider'

    type = fields.Selection(selection_add=[('turatel', 'Turatel')], ondelete={'turatel': 'cascade'})


class SmsApi(models.AbstractModel):
    _inherit = 'sms.api'

    @api.model
    def _get_turatel_credit_url(self):
        return 

    @api.model
    def _send_turatel_sms(self, messages, provider):
        params = {'messages': messages}
        result, message = self.env['syncops.connector'].sudo()._execute('sms_post_partner_otp', params=params, message=True)
        if result is None:
            raise UserError(message)

        return [{'res_id': message['res_id'], 'state': 'success'} for message in messages]

    @api.model
    def _get_turatel_credit(self, provider):
        pass
