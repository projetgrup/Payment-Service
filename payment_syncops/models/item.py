# -*- coding: utf-8 -*-
from pytz import timezone
from urllib.parse import urlparse
from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.addons.connector_syncops.models.config import DAYS


class PaymentItem(models.Model):
    _inherit = 'payment.item'

    syncops_ok = fields.Boolean(readonly=True)
    syncops_notif = fields.Boolean(readonly=True)
    syncops_data = fields.Text(string='syncOPS Data')

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
