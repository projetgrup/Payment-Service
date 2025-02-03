# -*- coding: utf-8 -*-
import requests
import pytz
from datetime import datetime, date
from dateutil import parser

from odoo import fields, models, api,_
from odoo.exceptions import UserError, ValidationError


class SyncopsLogWizard(models.TransientModel):
    _name = 'syncops.log.wizard'
    _description = 'SyncOPS Log Wizard'

    connector_id = fields.Many2one('syncops.connector', string='Connector', readonly=True, required=True)
    date_start = fields.Datetime(string='Start Date', required=True)
    date_end = fields.Datetime(string='End Date', required=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        today = date.today()
        user_tz = self.env.user.tz or self.env.context.get('tz')
        user_pytz = pytz.timezone(user_tz) if user_tz else pytz.utc
        offset = user_pytz.utcoffset(datetime.now())
        res['date_start'] = datetime.combine(today, datetime.min.time()) - offset
        res['date_end'] = datetime.combine(today, datetime.max.time()) - offset
        return res

    def confirm(self):
        if self.date_start >= self.date_end:
            raise UserError(_('Start date must be before end date'))

        result = []
        try:
            url = self.env['ir.config_parameter'].sudo().get_param('syncops.url')
            if not url:
                raise ValidationError(_('No syncOPS endpoint URL found'))

            user_tz = self.env.user.tz or self.env.context.get('tz')
            user_pytz = pytz.timezone(user_tz) if user_tz else pytz.utc
            offset = user_pytz.utcoffset(datetime.now())
 
            url += '/api/v1/log'
            response = requests.get(url, params={
                'username': self.connector_id.username,
                'token': self.connector_id.token,
                'start': (self.date_start + offset).isoformat(),
                'end': (self.date_end + offset).isoformat(),
            })
            if response.status_code == 200:
                results = response.json()
                if not results['status'] == 0:
                    raise UserError(results['message'])
                logs = results.get('logs', [])
                for log in logs:
                    result.append({
                        'connector_id': self.connector_id.id,
                        'company_id': self.env.company.id,
                        'date': parser.parse(log['date']),
                        'partner_name': log['partner'],
                        'connector_name': log['connector'],
                        'token_name': log['token'],
                        'method_name': log['method'],
                        'status': log['status'],
                        'state': log['state'],
                        'message': log['message'],
                        'request_data': log['request_data'],
                        'request_raw': log['request_raw'],
                        'request_method': log['request_method'],
                        'request_url': log['request_url'],
                        'response_code': log['response_code'],
                        'response_message': log['response_message'],
                        'response_data': log['response_data'],
                        'response_raw': log['response_raw'],
                    })
            else:
                raise UserError(response.text or response.reason)
        except Exception as e:
            raise UserError(str(e))
        
        if result:
            logs = self.env['syncops.log'].sudo().create(result)
            action = self.env.ref('connector_syncops.action_log').sudo().read()[0]
            action['context'] = {'create': False, 'delete': False, 'edit': False, 'import': False}
            action['domain'] = [('id', '=', logs.ids)]
            return action
        else:
            raise UserError(_('No log found'))
