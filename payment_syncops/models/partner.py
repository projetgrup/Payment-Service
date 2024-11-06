# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, api, fields


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def cron_sync(self):
        self = self.sudo()
        offset = timedelta(hours=3) # Turkiye Timezone
        now = datetime.now() + offset
        pre = now - timedelta(hours=1)
        for company in self.env['res.company'].search([('system', '!=', False), ('syncops_cron_sync_partner', '=', True)]):
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
