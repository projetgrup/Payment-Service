# -*- coding: utf-8 -*-
import traceback
import logging
import pytz
from datetime import datetime, timedelta
from urllib.parse import urlparse

from odoo import models, fields, api
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    paylox_notif_mail_state = fields.Boolean('Paylox Email Notification State', readonly=True)
    paylox_notif_sms_state = fields.Boolean('Paylox SMS Notification State', readonly=True)

    def _paylox_done_postprocess(self):
        res = super()._paylox_done_postprocess()
        self._paylox_send_done_mail()
        self._paylox_send_done_sms()
        return res

    def _paylox_send_done_mail(self):
        self.ensure_one()
        if self.paylox_notif_mail_state:
            return

        try:
            with self.env.cr.savepoint():
                company = self.company_id or self.env.company
                if not company.system or not company.notif_mail_success_ok:
                    return

                template = self.env.ref('payment_vendor.mail_transaction_successful')
                partner = self.partner_id
                commercial_partner = partner.commercial_partner_id
                followers = self.env['mail.followers'].search([('res_model', '=', 'res.partner'), ('res_id', '=', commercial_partner.id)])
                partners = followers.mapped('partner_id') | partner
                mail_server = company.mail_server_id

                context = self.env.context.copy()
                context.update({
                    'tx': self,
                    'company': company,
                    'server': mail_server,
                    'partner': self.partner_name,
                    'url': self.jetcheckout_website_id.domain,
                    'domain': urlparse(self.jetcheckout_website_id.domain).netloc,
                    'from': mail_server.email_formatted or company.email_formatted,
                })

                for partner in partners:
                    context.update({
                        'tz': partner.tz,
                        'lang': partner.lang,
                    })
                    template.with_context(context).send_mail(partner.id, force_send=True, email_values={
                        'is_notification': True,
                        'mail_server_id': mail_server.id,
                    })
                    self.paylox_notif_mail_state = True

        except Exception as e:
            _logger.error(traceback.format_exc())
            _logger.error('Sending email for transaction %s is failed\n%s' % (self.reference, e))
 
    def _paylox_send_done_sms(self):
        self.ensure_one()
        if self.paylox_notif_sms_state:
            return

        try:
            with self.env.cr.savepoint():
                company = self.company_id or self.env.company
                if not company.system or not company.notif_sms_success_ok:
                    return

                partner = self.partner_id
                commercial_partner = partner.commercial_partner_id
                followers = self.env['mail.followers'].search([('res_model', '=', 'res.partner'), ('res_id', '=', commercial_partner.id)])
                partners = followers.mapped('partner_id') | partner
                template = self.env.ref('payment_vendor.sms_transaction_successful')
                note = self.env['ir.model.data'].sudo()._xmlid_to_res_id('mail.mt_note')
                params = self.env['ir.config_parameter'].sudo().get_param
                provider = self.env['sms.provider'].get(company.id)
                if not provider and params('paylox.sms.default'):
                    id = int(params('paylox.sms.provider', '0'))
                    provider = self.env['sms.provider'].browse(id)

                amount = formatLang(self.env, self.amount)
                context = self.env.context.copy()
                context.update({
                    'tx': self,
                    'amount': amount,
                    'partner': commercial_partner,
                    'company': company,
                    'url': self.jetcheckout_website_id.domain,
                    'domain': urlparse(self.jetcheckout_website_id.domain).netloc,
                })

                messages = []
                for partner in partners:
                    context.update({
                        'tz': partner.tz,
                        'lang': partner.lang,
                    })
                    body = template.with_context(context)._render_field('body', [partner.id], set_lang=partner.lang)[partner.id]
                    sms_values = {
                        'partner_id': partner.id,
                        'body': body,
                        'number': partner.mobile,
                        'state': 'outgoing',
                        'provider_id': provider.id,
                    }
                    messages.append(sms_values)
                sendings = self.env['sms.sms'].create(messages)

                messages = []
                for sending in sendings:
                    messages.append({
                        'res_id': sending.partner_id.id,
                        'model': 'res.partner',
                        'message_type': 'sms',
                        'subtype_id': note,
                        'body': sending.body,
                        'notification_ids': [(0, 0, {
                            'res_partner_id': sending.partner_id.id,
                            'sms_number': sending.number,
                            'notification_type': 'sms',
                            'sms_id': sending.id,
                            'is_read': True,
                            'notification_status': 'ready',
                            'failure_type': '',
                        })]
                    })
                self.env['mail.message'].create(messages)
                self.env.ref('sms.ir_cron_sms_scheduler_action')._trigger()
                self.paylox_notif_sms_state = True

        except Exception as e:
            _logger.error('Sending sms for transaction %s is failed\n%s' % (self.reference, e))

    @api.model
    def paylox_send_daily_email(self):
        users = self.env.ref('payment_vendor.group_vendor_manager').mapped('users')
        template = self.env.ref('payment_vendor.mail_transaction_daily')
        now = datetime.now()

        for user in users:
            timezone = user[0].tz
            try:
                tz = pytz.timezone(timezone)
            except:
                tz = pytz.timezone('UTC')
            offset = tz.utcoffset(now)
            date_end = (now + offset).replace(hour=0, minute=0, second=0, microsecond=0)
            date_start = date_end - timedelta(days=1)

            for company in user.company_ids.filtered(lambda x: x.system == 'vendor'):
                websites = self.env['website'].sudo().search([('company_id', '=', company.id)])
                if not websites:
                    continue

                mail_server = company.mail_server_id
                context = self.env.context.copy()
                context['date'] = date_start.strftime('%d.%m.%Y')
                context['partner'] = user.partner_id
                context['company'] = company
                context['server'] = mail_server
                context['from'] = mail_server.email_formatted or company.email_formatted

                for website in websites:
                    context['url'] = website.domain
                    context['domain'] = urlparse(context['url']).netloc
                    context['transactions'] = []
                    context['total'] = 0

                    domain = [
                        ('company_id', '=', company.id),
                        ('create_date', '>=', date_start - offset),
                        ('create_date', '<', date_end - offset),
                        ('state', '=', 'done'),
                        ('jetcheckout_website_id', '=', website.id),
                    ]
                    if user.has_group('payment_jetcheckout_system.group_system_own_partner'):
                        domain.extend([
                            '|', '|',
                            ('partner_id', '=', user.partner_id.id),
                            ('partner_id.user_id', '=', user.id),
                            ('partner_id.parent_id.user_id', '=', user.id),
                        ])

                    transactions = self.env['payment.transaction'].sudo().read_group(domain, fields=['amount:sum'], groupby=['partner_id'], orderby='amount desc')
                    for transaction in transactions:
                        partner = self.env['res.partner'].sudo().browse(transaction['partner_id'][0])
                        context['transactions'].append({
                            'name': '[%s] %s' % (partner.ref, partner.name) if partner.ref else partner.name,
                            'amount': transaction['amount']
                        })
                        context['total'] += transaction['amount']

                    try:
                        with self.env.cr.savepoint():
                            template.with_context(context).send_mail(context['partner'].id, force_send=True, email_values={
                                'is_notification': True,
                                'mail_server_id': mail_server.id,
                            })
                    except Exception as e:
                        _logger.error('Sending daily email for partner %s is failed\n%s' % (context['partner'].name, e))

    #TODO Remove
    @api.model
    def jetcheckout_send_daily_email(self):
        self.paylox_send_daily_email()
