# -*- coding: utf-8 -*-
import requests
from pytz import timezone
from dateutil import parser
from urllib.parse import urlparse
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.connector_syncops.models.config import DAYS


class PaymentItem(models.Model):
    _inherit = 'payment.item'

    @api.depends('jetcheckout_connector_ok', 'jetcheckout_connector_sent', 'jetcheckout_connector_state', 'jetcheckout_connector_state_message')
    def _compute_jetcheckout_connector_result(self):
        for item in self:
            if item.jetcheckout_connector_ok:
                if item.jetcheckout_connector_sent:
                    if item.jetcheckout_connector_state:
                        item.jetcheckout_connector_result = '<i class="fa fa-times text-danger" title="%s"/>' % item.jetcheckout_connector_state_message
                    else:
                        item.jetcheckout_connector_result = '<i class="fa fa-check text-primary" title="%s"/>' % item.jetcheckout_connector_state_message
                else:
                    item.jetcheckout_connector_result = '<i class="fa fa-cog fa-spin" title="%s"/>' % _('Processing...')
            else:
                item.jetcheckout_connector_result = False

    syncops_ok = fields.Boolean(readonly=True)
    syncops_notif = fields.Boolean(readonly=True)
    syncops_data = fields.Text(string='syncOPS Data')
    jetcheckout_connector_ok = fields.Boolean('Connector', readonly=True)
    jetcheckout_connector_sent = fields.Boolean('Connector Sent', readonly=True)
    jetcheckout_connector_state = fields.Boolean('Connector State', readonly=True)
    jetcheckout_connector_state_message = fields.Text('Connector State Message', readonly=True)
    jetcheckout_connector_payment_ref = fields.Char('Connector Payment Reference', readonly=True)
    jetcheckout_connector_result = fields.Html('Connector Result', sanitize=False, compute='_compute_jetcheckout_connector_result')

    def action_check_connector(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        connector = self.env['syncops.connector'].sudo()._find('payment_post_partner_payment', company=company)
        if not connector:
            raise UserError(_('No syncOPS connector found'))

        if not self.id:
            raise UserError(_('Please save transaction before checking connector logs'))

        result = []
        try:
            url = self.env['ir.config_parameter'].sudo().get_param('syncops.url')
            if not url:
                raise ValidationError(_('No syncOPS endpoint URL found'))

            url += '/api/v1/log'
            response = requests.get(url, params={
                'username': connector.username,
                'token': connector.token,
                'reference': str(self.id),
            })
            if response.status_code == 200:
                results = response.json()
                if not results.get('status') == 0:
                    raise UserError(results['message'])
                logs = results.get('logs', [])
                for log in logs:
                    result.append({
                        'connector_id': connector.id,
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
                        'request_method': log['request_method'],
                        'request_url': log['request_url'],
                        'response_code': log['response_code'],
                        'response_message': log['response_message'],
                        'response_data': log['response_data'],
                    })
            else:
                raise UserError(response.text or response.reason)
        except Exception as e:
            raise UserError(str(e))

        if result:
            logs = self.env['syncops.log'].sudo().create(result)
            action = self.env.ref('connector_syncops.action_log').sudo().read()[0]
            action['context'] = {'create': False, 'delete': False, 'edit': False, 'import': False}
            action['domain'] = [('id', 'in', logs.ids)]
            return action
        else:
            raise UserError(_('No log found'))

    def action_process_connector(self):
        self.ensure_one()
        if self.paid and self.jetcheckout_connector_ok and self.jetcheckout_connector_state:
            result, message = self.env['syncops.connector'].sudo()._execute('payment_post_partner_payment', reference=str(self.id), params={
                'reference': self.description or '',
            }, company=self.company_id, message=True)

            if result is None:
                values = {
                    'jetcheckout_connector_sent': True,
                    'jetcheckout_connector_state': True,
                    #'jetcheckout_connector_payment_ref': False,
                    'jetcheckout_connector_state_message': _('This transaction has not been successfully posted to connector.\n%s') % message
                }
            else:
                values = {
                    'jetcheckout_connector_sent': True,
                    'jetcheckout_connector_state': False,
                    #'jetcheckout_connector_payment_ref': result and result[0].get('ref', False) or False,
                    'jetcheckout_connector_state_message': _('This transaction has been successfully posted to connector.')
                }
            self.write(values)
            self.flush()

    @api.model
    def cron_sync(self):
        self = self.sudo()
        now = datetime.now()
        tz = timezone('Europe/Istanbul')
        now += tz.utcoffset(now)
        pre = now - timedelta(hours=1)
        companies = self.env['res.company'].search([
            ('system', '!=', False),
            ('syncops_cron_sync_item', '=', True),
            ('syncops_cron_sync_item_subtype', '!=', False),
        ])
        for company in companies:
            days = map(lambda d: DAYS[d], company.syncops_cron_sync_item_day_ids.mapped('code'))
            if now.weekday() in days:
                hour = company.syncops_cron_sync_item_hour % 24
                time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                if pre < time <= now:
                    wizard = self.env['syncops.sync.wizard'].create({
                        'type': 'item',
                        'system': company.system,
                        'type_item_subtype': company.syncops_cron_sync_item_subtype,
                    })
                    wizard.with_company(company.id).confirm()
                    wizard.with_company(company.id).with_context(wizard_id=wizard.id).sync()
                    wizard.unlink()

    @api.model
    def cron_sync_notif(self):
        self = self.sudo()
        now = datetime.now()
        tz = timezone('Europe/Istanbul')
        now += tz.utcoffset(now)
        pre = now - timedelta(hours=1)
        companies = self.env['res.company'].search([
            ('system', '!=', False),
            ('syncops_cron_sync_item', '=', True),
            ('syncops_cron_sync_item_notif_ok', '=', True),
        ])
        for company in companies:
            try:
                hour = company.syncops_cron_sync_item_notif_hour % 24
                time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                if pre < time <= now:
                    items = self.env['payment.item'].search([
                        ('syncops_ok', '=', True),
                        ('syncops_notif', '=', True),
                        ('company_id', '=', company.id),
                        ('system', '=', company.system),
                    ])
                    if items:
                        partners = set()
                        context = self.env.context.copy()
                        params = self.env['ir.config_parameter'].sudo().get_param
                        types = company.syncops_cron_sync_item_notif_type_ids.mapped('code')

                        if 'email' in types:
                            mail_server = company.mail_server_id
                            email_from = mail_server.email_formatted or company.email_formatted
                            context.update({'server': mail_server, 'from': email_from, 'company': company})
                            mail_template = self.env.ref('payment_syncops.mail_template_item_notif')
                        if 'sms' in types:
                            sms_template = self.env.ref('payment_syncops.sms_template_item_notif')
                            sms_provider = self.env['sms.provider'].get(company.id)
                            if not sms_provider and params('paylox.sms.default'):
                                id = int(params('paylox.sms.provider', '0'))
                                sms_provider = self.env['sms.provider'].browse(id)

                        for item in items:
                            if item.parent_id.id in partners:
                                item.syncops_notif = False
                                continue

                            if 'email' in types:
                                try:
                                    with self.env.cr.savepoint():
                                        mail_template.with_context(
                                            **context,
                                            partner=item.parent_id,
                                            lang=item.parent_id.lang,
                                            link=item.parent_id._get_payment_url(),
                                        ).send_mail(
                                            item.parent_id.id,
                                            force_send=True,
                                            email_values={
                                                'is_notification': True,
                                                'mail_server_id': mail_server.id,
                                            }
                                        )
                                except:
                                    pass

                            if 'sms' in types:
                                try:
                                    with self.env.cr.savepoint():
                                        link = item.parent_id._get_payment_url()
                                        body = sms_template.with_context(
                                            **context,
                                            link=link,
                                            partner=item.parent_id,
                                            lang=item.parent_id.lang,
                                            domain=urlparse(link).netloc,
                                        )._render_field('body', [item.parent_id.id], set_lang=item.parent_id.lang)[item.parent_id.id]
                                        sms_values = {
                                            'partner_id': item.parent_id.id,
                                            'body': body,
                                            'number': item.parent_id.mobile,
                                            'state': 'outgoing',
                                            'provider_id': sms_provider.id,
                                        }
                                        sms_message = self.env['sms.sms'].sudo().create(sms_values)
                                        sms_message.send(unlink_failed=False, unlink_sent=True, raise_exception=False)
                                except:
                                    pass

                            item.syncops_notif = False
                            partners.add(item.parent_id.id)

                        self.env.cr.commit()
            except:
                self.env.cr.rollback()
