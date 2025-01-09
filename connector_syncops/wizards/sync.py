# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class SyncopsSyncWizard(models.TransientModel):
    _name = 'syncops.sync.wizard'
    _description = 'syncOPS Sync Wizard'

    type = fields.Char()
    line_ids = fields.One2many('syncops.sync.wizard.line', 'wizard_id', 'Lines')

    def _show_options(self):
        return False

    def confirm(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sync'),
            'domain': [('wizard_id', '=', self.id)],
            'res_model': 'syncops.sync.wizard.line',
            'context': {'dialog_size': 'large', 'wizard_id': self.id},
            'view_mode': 'tree',
            'target': 'new',
        }

    def sync(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def action_sync(self):
        wizard = self.create({})
        if wizard._show_options():
            return {
                'type': 'ir.actions.act_window',
                'name': _('Sync'),
                'res_id': wizard.id,
                'res_model': 'syncops.sync.wizard',
                'context': {'dialog_size': 'small'},
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            return wizard.confirm()


class SyncopsSyncWizardLine(models.TransientModel):
    _name = 'syncops.sync.wizard.line'
    _description = 'syncOPS Sync Wizard Lines'

    wizard_id = fields.Many2one('syncops.sync.wizard')
    name = fields.Char(readonly=True)
    data = fields.Text(readonly=True)
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', readonly=True, default=lambda self: self.env.company.currency_id)

    def remove(self):
        self.unlink()
        return {'type': 'syncops.sync.wizard.reload'}


class SyncopsSyncWizardReload(models.AbstractModel):
    _name = 'syncops.sync.wizard.reload'
    _description = 'syncOPS Sync Wizard Reload'

    def _get_readable_fields(self):
        return {}
