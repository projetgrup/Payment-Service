# -*- coding: utf-8 -*-
from urllib.parse import urlparse
from odoo import models, fields, _
from odoo.exceptions import UserError


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _compute_paylox_agreement_count(self):
        for tx in self:
            tx.paylox_agreement_count = len(tx.paylox_agreement_ids)

    paylox_agreement_count = fields.Integer(compute='_compute_paylox_agreement_count')
    paylox_agreement_ids = fields.One2many('payment.transaction.agreement', 'transaction_id', 'Agreements', readonly=False)

    def action_agreement(self):
        self.ensure_one()
        action = self.env.ref('payment_system_agreement.action_transaction_agreement').sudo().read()[0]
        if len(self.paylox_agreement_ids) == 0:
            raise UserError(_('No agreement found'))
        elif len(self.paylox_agreement_ids) == 1:
            action['res_id'] = self.paylox_agreement_ids.id
            action['views'] = [[False, 'form']]
        else:
            action['domain'] = [('id', 'in', self.paylox_agreement_ids.ids)]
        return action

    def _paylox_done_postprocess(self):
        res = super()._paylox_done_postprocess()
        agreements = self.env['payment.transaction.agreement'].sudo().search([
            ('transaction_id', '=', self.id),
            ('active', '=', False),
        ])
        for agreement in agreements:
            agreement.write({
                'active': True,
                'partner_id': self.partner_id.id,
                'ip_address': self.jetcheckout_ip_address,
                'path': urlparse(self.jetcheckout_url_address).path,
                'body': agreement.render(),
            })
        return res
