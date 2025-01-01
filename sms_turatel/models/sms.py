# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError


ERRORS = {
    None: ValidationError('Bir hata meydana geldi'),
    '-1': AccessError('A user with the provided information could not be found.'),
    '-2': AccessError('The user is inactive.'),
    '-3': ValidationError('The user is blocked.'),
    '-4': ValidationError('The user account could not be found.'),
    '-5': AccessError('The user account is inactive.'),
    '-6': AccessError('No record found.'),
    '-7': ValidationError('Invalid XML request structure.'),
    '-8': AccessError('One or more of the received parameters are incorrect.'),
    '-9': AccessError('Prepaid account not found.'),
    '-10': AccessError('Temporary outage in the operator service.'),
    '-11': AccessError('The difference between the start date and the current time is less than 30 minutes.'),
    '-12': AccessError('The difference between the end date and the current time is more than 30 days.'),
    '-13': AccessError('Invalid sender information.'),
    '-14': AccessError('No SMS sending permission for the account.'),
    '-15': AccessError('The message content is empty or exceeds the character limit.'),
    '-16': AccessError('Invalid recipient information.'),
    '-17': AccessError('The number of parameters does not match the number of parameters in the template.'),
    '-18': AccessError('Multiple errors in the submission. MessageId should be checked.'),
    '-19': AccessError('Duplicate submission request.'),
    '-20': AccessError('The user does not wish to receive notification messages.'),
    '-21': AccessError('The number is on the blacklist.'),
    '-22': AccessError('Unauthorized IP address.'),
    '-23': AccessError('User does not have permission.'),
    '-24': AccessError('The specified package has already been approved.'),
    '-25': AccessError('No unapproved package found for the specified ID.'),
    '-26': AccessError('The commitment period has expired.'),
    '-27': AccessError('The commitment amount has been exceeded.'),
    '-28': AccessError('The user has exceeded their sending limit.'),
    '-29': AccessError('The start date cannot be later than the end date.'),
    '-30': AccessError('The sending was canceled due to the failure to check the blacklist.'),
    '-40': AccessError('Invalid MMS file format. Only (3gp, gif, jpg, jpeg, png) formats are supported.'),
    '-41': AccessError('MMS file is empty or does not meet the specified criteria.'),
    '-1000': AccessError('SYSTEM_ERROR'),
}


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
        params = {
            'messages': messages,
        }

        result, message = self.env['syncops.connector'].sudo()._execute('sms_post_partner_otp', params=params, message=True)
        res = result[0]
        if res['ErrorCode'] == 0:
            return [{'res_id': message['res_id'], 'state': 'success'} for message in messages]
        else:
            raise ERRORS.get(res['ErrorCode'], ERRORS[None])

    @api.model
    def _get_turatel_credit(self, provider):
        raise ERRORS.get(None, ERRORS[None])
