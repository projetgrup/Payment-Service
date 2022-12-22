# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError

class PaymentAcquirerJetcheckoutApiApplication(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.api.application'
    _description = 'Jetcheckout Application'
    _remote_name = 'jet.application'

    acquirer_id = fields.Many2one('payment.acquirer')
    parent_id = fields.Many2one('payment.acquirer.jetcheckout.api.applications')
    virtual_pos_ids = fields.Many2many('payment.acquirer.jetcheckout.api.pos', 'payment_jetcheckout_api_application_pos_rel', 'application_id', 'pos_id', string='Poses', ondelete='cascade')
    res_id = fields.Integer(readonly=True)
    in_use = fields.Boolean(readonly=True)
    name = fields.Char(required=True)
    application_id = fields.Char('Application ID', readonly=True)
    secret_key = fields.Char('Secret Key', readonly=True)
    is_active = fields.Boolean('Active', default=True)
    first_selection = fields.Selection([
        ('CardBank', 'Card Bank'),
        ('LowCostRate', 'Low Cost Rate'),
        ('Priority', 'Priority'),
    ], string='First Selection Criteria')
    second_selection = fields.Selection([
        ('CardBank', 'Card Bank'),
        ('LowCostRate', 'Low Cost Rate'),
        ('Priority', 'Priority'),
    ], string='Second Selection Criteria')
    third_selection = fields.Selection([
        ('CardBank', 'Card Bank'),
        ('LowCostRate', 'Low Cost Rate'),
        ('Priority', 'Priority'),
    ], string='Third Selection Criteria')
    virtual_poses = fields.Char('Virtual Pos', readonly=True)

    def select(self):
        if not self.is_active:
            raise UserError(_('Please activate this record before selecting it'))

        acquirer = self.acquirer_id
        acquirer.write({
            'jetcheckout_api_name': self.name,
            'jetcheckout_api_key': self.application_id,
            'jetcheckout_secret_key': self.secret_key
        })

        ids, journals = [], []
        pos_ids = self.virtual_pos_ids
        for pos in pos_ids.filtered(lambda x: x.is_active):
            ids.append(pos.id)
            line = acquirer.jetcheckout_journal_ids.filtered(lambda x: x.res_id == pos.id)
            if line:
                journals.append((1, line.id, {'name': pos.name}))
            else:
                journals.append((0, 0, {
                    'res_id': pos.id,
                    'name': pos.name,
                    'company_id': self.acquirer_id.company_id.id,
                    'website_id': self.acquirer_id.website_id.id
                }))

        for line in acquirer.jetcheckout_journal_ids.filtered(lambda x: x.res_id not in ids):
            journals.append((2, line.id, 0))

        acquirer.jetcheckout_journal_ids = journals
        acquirer._jetcheckout_api_sync_campaign(pos_ids)

    def write(self, vals):
        if 'name' in vals:
            for app in self:
                if app.in_use:
                    app.acquirer_id.jetcheckout_api_name = vals['name']
                    break
        return super().write(vals)

    def unlink(self):
        if 'application' in self.env.context:
            for app in self:
                if app.in_use:
                    app.acquirer_id.jetcheckout_api_key = False
                    app.acquirer_id.jetcheckout_secret_key = False
                    app.acquirer_id.jetcheckout_journal_ids = [(5, 0, 0)]
                    break
        return super().unlink()

class PaymentAcquirerJetcheckoutApiApplications(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.api.applications'
    _description = 'Jetcheckout Applications'

    acquirer_id = fields.Many2one('payment.acquirer')
    application_ids = fields.One2many('payment.acquirer.jetcheckout.api.application', 'parent_id', 'Applications')

    def write(self, vals):
        data = self.acquirer_id._jetcheckout_api_read()
        self.acquirer_id._jetcheckout_api_upload(vals, data, self)
        self.acquirer_id._jetcheckout_api_sync_campaign(self.application_ids.virtual_pos_ids)
        return super().write(vals)
