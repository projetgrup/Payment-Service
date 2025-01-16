# -*- coding: utf-8 -*-
import json
import logging
import datetime
import traceback

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval, test_python_expr

_logger = logging.getLogger(__name__)

class _json:
    loads = json.loads
    dumps = json.dumps


class PaymentHook(models.Model):
    _name = 'payment.hook'
    _description = 'Payment Hooks'

    def _compute_name(self):
        for hook in self:
            hook.name = _('Hook #%s') % (hook.id or '?',)

    company_id = fields.Many2one('res.company', ondelete='cascade', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    name = fields.Char(compute='_compute_name')
    system = fields.Selection([])
    code = fields.Text()
    type = fields.Selection([
        ('transaction', 'Transaction'),
        ('route', 'Route'),
    ])
    subtype = fields.Selection([
        ('create', 'Creation'),
        ('finalize', 'Finalization'),
    ])

    @api.constrains('code')
    def _check_code(self):
        for hook in self.sudo().filtered('code'):
            msg = test_python_expr(expr=hook.code.strip(), mode='exec')
            if msg:
                raise ValidationError(msg)

    def run(self, **kwargs):
        context = {
            'env': self.env,
            #'datetime': datetime,
            'UserError': UserError,
            'json': _json,
            **kwargs
        }
        try:
            for hook in self:
                safe_eval(hook.code.strip(), context, mode='exec', nocopy=True)
        except UserError:
            raise
        except:
            _logger.error(traceback.format_exc())
            raise ValidationError(_('An error occured when triggering the hook.'))
