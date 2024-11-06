# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api


class PaymentItem(models.Model):
    _inherit = 'payment.item'

    syncops_ok = fields.Boolean(readonly=True)
    syncops_notif = fields.Boolean(readonly=True)

    @api.model
    def cron_sync(self):
        self = self.sudo()
        offset = timedelta(hours=3) # Turkiye Timezone
        now = datetime.now() + offset
        pre = now - timedelta(hours=1)
        companies = self.env['res.company'].search([
            ('system', '!=', False),
            ('syncops_cron_sync_item', '=', True),
            ('syncops_cron_sync_item_subtype', '!=', False),
        ])
        for company in companies:
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
        offset = timedelta(hours=3) # Turkiye Timezone
        now = datetime.now() + offset
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
                        mail_server = company.mail_server_id
                        email_from = mail_server.email_formatted or company.email_formatted
                        context.update({'server': mail_server, 'from': email_from, 'company': company})
                        template = self.env.ref('payment_syncops.mail_template_item_notif')

                        for item in items:
                            if item.parent_id.id in partners:
                                item.syncops_notif = False
                                continue

                            try:
                                with self.env.cr.savepoint():
                                    template.with_context(
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
                                    item.syncops_notif = False
                                    partners.add(item.parent_id.id)
                            except:
                                pass

                        self.env.cr.commit()
            except:
                self.env.cr.rollback()
