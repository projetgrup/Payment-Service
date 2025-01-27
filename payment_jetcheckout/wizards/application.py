# -*- coding: utf-8 -*-
from odoo import fields, models, api, SUPERUSER_ID, _
from odoo.exceptions import UserError


class PaymentPayloxApiApplication(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.api.application'
    _description = 'Paylox API Application'
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
            ids.append(pos.res_id)
            line = acquirer.paylox_journal_ids.filtered(lambda x: x.res_id == pos.res_id)
            if line:
                journals.append((1, line.id, {'name': pos.name}))
            else:
                journals.append((0, 0, {
                    'res_id': pos.res_id,
                    'name': pos.name,
                    'company_id': self.acquirer_id.company_id.id,
                    'website_id': self.acquirer_id.website_id.id
                }))

        for line in acquirer.paylox_journal_ids.filtered(lambda x: x.res_id not in ids):
            journals.append((2, line.id, 0))

        acquirer.paylox_journal_ids = journals
        acquirer._paylox_api_sync_campaign(poses=pos_ids)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'redirect_acquirer',
            'params': {
                'back': True,
                'id': self.acquirer_id.id,
            }
        }

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if 'res_id' not in vals:
            id = res.acquirer_id._rpc(res, 'create', vals)
            res.write({'res_id': id})
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'res_id' not in vals:
            for app in self:
                app.acquirer_id._rpc(app, 'write', app.res_id, vals)
                app.acquirer_id._paylox_api_sync_campaign()

        if 'name' in vals:
            for app in self:
                if app.in_use:
                    app.acquirer_id.jetcheckout_api_name = vals['name']
                    break

        return res

    def unlink(self):
        if self.env.uid == SUPERUSER_ID:
            return super().unlink()

        if 'application' in self.env.context:
            for app in self:
                if app.in_use:
                    app.acquirer_id.jetcheckout_api_key = False
                    app.acquirer_id.jetcheckout_secret_key = False
                    app.acquirer_id.paylox_journal_ids = [(5, 0, 0)]
                    break
                
        if not self.env.context.get('no_sync'):
            for app in self:
                app.acquirer_id._rpc(app._remote_name, 'unlink', app.res_id)
        return super().unlink()

class PaymentPayloxApiApplications(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.api.applications'
    _description = 'Paylox API Applications'

    acquirer_id = fields.Many2one('payment.acquirer')
    application_ids = fields.One2many('payment.acquirer.jetcheckout.api.application', 'parent_id', 'Applications')

    def write(self, vals):
        data = self.acquirer_id._paylox_api_read()
        self.acquirer_id._paylox_api_upload(vals, data, self)
        self.acquirer_id._paylox_api_sync_campaign()
        return super().write(vals)
