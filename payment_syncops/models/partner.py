# -*- coding: utf-8 -*-
from pytz import timezone
from datetime import datetime, timedelta
from odoo import models, api, fields
from odoo.addons.connector_syncops.models.config import DAYS


class Partner(models.Model):
    _inherit = 'res.partner'

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
            ('syncops_cron_sync_partner', '=', True),
            ('syncops_cron_sync_item_subtype', '!=', False),
        ])
        for company in companies:
            days = map(lambda d: DAYS[d], company.syncops_cron_sync_partner_day_ids.mapped('code'))
            if now.weekday() in days:
                hour = company.syncops_cron_sync_partner_hour % 24
                time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                if pre < time <= now:
                    wizard = self.env['syncops.sync.wizard'].create({
                        'type': 'partner',
                        'system': company.system,
                    })
                    wizard.with_company(company.id).confirm()
                    wizard.with_company(company.id).with_context(wizard_id=wizard.id).sync()
                    wizard.unlink()


class PartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def _paylox_api_save(self, acquirer, method, data):
        user = self.env.user
        partner = self.partner_id
        company = partner.company_id or self.env.company
        if company.syncops_check_iban and user.has_group('payment_syncops.group_check_iban'):
            iban = self.env['syncops.partner.iban'].sudo().search([('name', '=', data['iban'])])
            if not iban:
                result, message = self.env['syncops.connector'].sudo()._execute('other_get_ozan_iban', reference=str(self.id), params={
                    'vat': data['tax_number'],
                    'iban': data['iban'],
                }, company=self.env.company, message=True)
                if result is None:
                    return {'state': False, 'message': message}
                elif not result[0]['ok']:
                    return {'state': False, 'message': result[0]['message']}
                iban.create({'name': data['iban']})
        return super()._paylox_api_save(acquirer, method, data)


class SyncopsPartnerIban(models.Model):
    _name = 'syncops.partner.iban'
    _description = 'syncOPS Partner Bank IBAN'

    name = fields.Char()
