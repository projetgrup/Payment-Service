# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PaymentItem(models.Model):
    _inherit = 'payment.item'

    system = fields.Selection(selection_add=[('supplier', 'Supplier Payment System')])
    system_supplier_plan_mail_sent = fields.Boolean(readonly=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.company.system == 'supplier':
            res['mail_ok'] = True
        return res
 
    def send_done_mail(self):
        if self.env.company.system == 'supplier':
            try:
                if self.mail_ok and not self.mail_sent:
                    with self.env.cr.savepoint():
                        mail_server = self.company_id.mail_server_id
                        email_from = mail_server.email_formatted or self.company_id.email_formatted
                        iban = self.parent_id.bank_ids.filtered(lambda bank: bank.api_state and bank.acc_number)
                        context = self.env.context.copy()
                        context.update({
                            'server': mail_server,
                            'from': email_from,
                            'company': self.company_id,
                            'partner': self.parent_id,
                            'lang': self.parent_id.lang,
                            'iban': iban and iban[0].acc_number.replace(' ', '') or ''
                        })
                        template = self.env.ref('payment_supplier.mail_item_done')
                        template.with_context(context).send_mail(self.parent_id.id, force_send=True, email_values={
                            'is_notification': True,
                            'mail_server_id': mail_server.id,
                        })
                        self.mail_sent = True
            except Exception as e:
                ids = ', '.join(map(str, self.mapped('parent_id.id')))
                _logger.error('An error occured when sending payment item done email to partner(s) %s (%s)' % (ids, e))

        return super().send_done_mail()
