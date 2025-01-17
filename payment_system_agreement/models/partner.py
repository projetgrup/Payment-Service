# -*- coding: utf-8 -*-
from urllib.parse import urlparse
from odoo import models, fields, _
from odoo.exceptions import UserError


class Partner(models.Model):
    _inherit = 'res.partner'

    def _compute_paylox_agreement_count(self):
        for tx in self:
            tx.paylox_agreement_count = len(tx.paylox_agreement_ids)

    paylox_agreement_count = fields.Integer(compute='_compute_paylox_agreement_count')
    paylox_agreement_ids = fields.One2many('payment.transaction.agreement', 'partner_id', 'Agreements', readonly=False)

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
