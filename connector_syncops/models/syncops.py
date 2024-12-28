# -*- coding: utf-8 -*-
import requests
import logging
import traceback
from datetime import datetime

from odoo import models, api, fields, _
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.exceptions import RedirectWarning, ValidationError, UserError

_logger = logging.getLogger(__name__)


class SyncopsConnector(models.Model):
    _name = 'syncops.connector'
    _description = 'syncOPS Connectors'
    _order = 'id DESC'

    name = fields.Char(required=True)
    username = fields.Char(string='Username', required=True)
    token = fields.Char(string='Token', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, ondelete='cascade', required=True, readonly=True)
    company_ids = fields.Many2many('res.company', 'syncops_company_rel', 'connector_id', 'company_id', string='Related Companies')
    line_ids = fields.One2many('syncops.connector.line', 'connector_id', string='Lines')
    active = fields.Boolean(default=True)
    connected = fields.Boolean(readonly=True)
    environment = fields.Boolean(default=False)

    @api.constrains('token')
    def _check_token(self):
        for connector in self:
            same_connector = self.sudo().with_context({'active_test': False}).search_count([('id', '!=', connector.id), ('token', '=', connector.token)])
            if same_connector:
                raise UserError(_('This token is already exist. Please ensure that it is correct.'))

    @api.model
    def _find(self, method=None, company=None):
        if not company:
            company = self.env.company
        
        domain = [('company_id', '=', company.id), ('connected', '=', True)]
        if method:
            domain += [('line_ids.code', '=', method)]

        return self.search(domain)

    @api.model
    def _defaults(self, connector, method, io, values):
        defaults = {}
        lines = connector.line_ids.filtered(lambda x: x.code == method)
        for line in lines:
            defaults.update(line._defaults(io, values))
        return defaults

    @api.model
    def _execute(self, method, reference='', params={}, company=None, message=None):
        result = []
        try:
            if not company:
                company = self.env.company

            connectors = self._find(method, company)
            if not connectors:
                info = _('No connector found for %s') % company.name
                _logger.info(info)
                return (None, info) if message else None

            url = self.env['ir.config_parameter'].sudo().get_param('syncops.url')
            if not url:
                raise ValidationError(_('No syncOPS endpoint URL found'))

            for connector in connectors:
                lines = connector.line_ids.filtered(lambda l: l.code == method)
                for line in lines:
                    defaults = line._defaults('input', params)
                    params.update(defaults)

                    url += '/api/v1/execute'
                    response = requests.post(url, json={
                        'username': connector.username,
                        'token': connector.token,
                        'method': method,
                        'params': params,
                        'line': line.res_id,
                        'reference': reference,
                        'environment': connector.environment and 'P' or 'T',
                    })
                    if response.status_code == 200:
                        results = response.json()
                        if not results['status'] == 0:
                            _logger.error('An error occured when executing method %s for %s: %s' % (method, company and company.name or '', results['message']))
                            return (None, results['message']) if message else None
                        result += results.get('result', [])
                    else:
                        _logger.error('An error occured when executing method %s for %s: %s' % (method, company and company.name or '', response.text or response.reason))
                        return (None, response.text or response.reason) if message else None

        except Exception as e:
            _logger.error('An error occured when executing method %s for %s: %s' % (method, company and company.name or '', e))
            _logger.error(traceback.format_exc())
            return (None, str(e)) if message else None

        return (result, None) if message else result

    def _connect(self, no_commit=False):
        url = self.env['ir.config_parameter'].sudo().get_param('syncops.url')
        if not url:
            self.write({
                'connected': False,
                'line_ids': [(5, 0, 0)],
            })
            if not no_commit:
                self.env.cr.commit()

            if self.env.user.has_group('base.group_system'):
                action = self.env.ref('connector_syncops.action_syncops_config_settings')
                message = _('You must specify a syncOPS endpoint URL address in settings')
                raise RedirectWarning(message, action.id, _('Go to settings'))
            else:
                raise ValidationError(_('Connection error is occured. Please contact with system administrator.'))

        url += '/api/v1/connect'
        result = {}
        for connector in self:
            try:
                response = requests.post(url, json={'username': connector.username, 'token': connector.token})
                if response.status_code == 200:
                    result = response.json()
                    if result['status'] == 0:
                        ids = connector.line_ids.ids
                        for line in connector.line_ids:
                            method = next(filter(lambda m: m['id'] == line.id, result['methods']), None)
                            if method:
                                line.write({
                                    'res_id': method['id'],
                                    'name': method['name'],
                                    'code': method['code'],
                                    'method': method['method'],
                                    'category': method['category'],
                                    'input_ids': [(5, 0, 0)] + [(0, 0, {
                                        'res_id': i['id'],
                                        'input': i['input'],
                                        'input_type': i['input_type'],
                                        'output': i['output'],
                                        'output_type': i['output_type'],
                                        'name': i['name'],
                                    }) for i in method['inputs']],
                                    'output_ids': [(5, 0, 0)] + [(0, 0, {
                                        'res_id': o['id'],
                                        'input': o['input'],
                                        'input_type': o['input_type'],
                                        'output': o['output'],
                                        'output_type': o['output_type'],
                                        'name': o['name'],
                                    }) for o in method['outputs']],
                                })
                            else:
                                line.unlink()

                        for method in result['methods']:
                            if method['id'] in ids:
                                continue

                            connector.write({
                                'line_ids': [(0, 0, {
                                    'res_id': method['id'],
                                    'name': method['name'],
                                    'code': method['code'],
                                    'method': method['method'],
                                    'category': method['category'],
                                    'input_ids': [(0, 0, {
                                        'res_id': i['id'],
                                        'input': i['input'],
                                        'input_type': i['input_type'],
                                        'output': i['output'],
                                        'output_type': i['output_type'],
                                        'name': i['name'],
                                    }) for i in method['inputs']],
                                    'output_ids': [(0, 0, {
                                        'res_id': o['id'],
                                        'input': o['input'],
                                        'input_type': o['input_type'],
                                        'output': o['output'],
                                        'output_type': o['output_type'],
                                        'name': o['name'],
                                    }) for o in method['outputs']],
                                })]
                            })

                        result[connector.id] = {
                            'type': 'info',
                            'title': _('Success'),
                            'message': _('Connection is succesful')
                        }
                    else:
                        connector.write({
                            'connected': False,
                        })
                        result[connector.id] = {
                            'type': 'danger',
                            'title': _('Error'),
                            'message': _('An error occured when connecting: %s' % result['message'])
                        }
                else:
                    connector.write({
                        'connected': False,
                    })
                    result[connector.id] = {
                        'type': 'danger',
                        'title': _('Error'),
                        'message': _('An error occured when connecting: %s' % response.reason)
                    }
            except Exception as e:
                _logger.error(traceback.format_exc())
                connector.write({
                    'connected': False,
                })
                result[connector.id] = {
                    'type': 'danger',
                    'title': _('Error'),
                    'message': _('An error occured when connecting: %s' % e)
                }
        return result

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res._connect(no_commit=True)
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'username' in vals or 'token' in vals:
            self._connect()
        return res

    @api.model
    def count(self, method, company=None):
        if not company:
            company = self.env.company

        return self.search_count([
            ('company_id', '=', company.id),
            ('connected', '=', True),
            ('line_ids.code', '=', method)
        ])

    def get_company_ids(self):
        return self.company_id.ids + self.company_ids.ids

    def action_toggle_environment(self):
        self.ensure_one()
        self.environment = not self.environment

    def action_toggle_active(self):
        self.ensure_one()
        self.active = not self.active

    def action_connect(self):
        self.ensure_one()
        result = self._connect()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
                **result[self.id]
            }
        }

    def action_view_log(self):
        self.ensure_one()
        self.env['syncops.log'].sudo().search([('connector_id', '=', self.id)]).unlink()
        action = self.env.ref('connector_syncops.action_log_wizard').sudo().read()[0]
        action['context'] = {'dialog_size': 'small', 'create': False, 'delete': False, 'default_connector_id': self.id}
        return action


class SyncopsConnectorLine(models.Model):
    _name = 'syncops.connector.line'
    _description = 'syncOPS Connector Line'

    connector_id = fields.Many2one('syncops.connector', 'Connector', index=True, ondelete='cascade')
    res_id = fields.Integer(string='Remote ID', readonly=True)
    name = fields.Char(string='Method', readonly=True)
    code = fields.Char(string='Code', readonly=True)
    category = fields.Char(string='Category', readonly=True)
    method = fields.Boolean(string='State', readonly=True)
    input_ids = fields.One2many('syncops.connector.line.input', 'line_id', 'Inputs', copy=True, readonly=True)
    output_ids = fields.One2many('syncops.connector.line.output', 'line_id', 'Outputs', copy=True, readonly=True)

    def _defaults(self, io, values):
        names = getattr(self, '%s_ids' % io).mapped('input')
        defaults = self.env['syncops.connector.line.default'].sudo().search([
            ('connector_id', '=', self.connector_id.id),
            ('io', '=', io),
            ('name', 'in', names),
            ('method', '=', self.code),
            ('type', 'in', ('const', 'code')),
        ])
        return {default.name: default._value(values) for default in defaults}


class SyncopsConnectorLineIO(models.AbstractModel):
    _name = 'syncops.connector.line.io'
    _description = 'syncOPS Connector Line IO'

    def _compute_direction(self):
        for line in self:
            line.direction = '→'

    def _compute_default(self):
        for line in self:
            connector = line.line_id.connector_id
            io = line._name.rsplit('.', 1)[-1]
            name = getattr(line, 'input')
            method = line.line_id.code
            default = self.env['syncops.connector.line.default'].search([
                ('connector_id', '=', connector.id),
                ('name', '=', name),
                ('method', '=', method),
                ('io', '=', io),
            ], limit=1)
            if default:
                line.default_ok = default.type in ('const', 'code')
                line.default_type = default.type
                line.default_const = default.const
                line.default_code = default.code
            else:
                line.default_ok = False
                line.default_type = 'none'
                line.default_const = False
                line.default_code = False

    line_id = fields.Many2one('syncops.connector.line', ondelete='cascade')
    res_id = fields.Integer(string='Remote ID', readonly=True)
    input = fields.Char('Input', readonly=True)
    input_type = fields.Char('Input Type', readonly=True)
    output = fields.Char('Output', readonly=True)
    output_type = fields.Char('Output Type', readonly=True)
    name = fields.Char('Description', readonly=True)
    direction = fields.Char(compute='_compute_direction', readonly=True)
    default_ok = fields.Boolean(compute='_compute_default')
    default_type = fields.Selection([
        ('none', 'None'),
        ('const', 'Constant'),
        ('code', 'Code'),
    ], compute='_compute_default')
    default_const = fields.Char(compute='_compute_default')
    default_code = fields.Text(compute='_compute_default')

    def action_default(self):
        connector = self.line_id.connector_id
        io = self._name.rsplit('.', 1)[-1]
        name = getattr(self, 'input')
        method = self.line_id.code
        default = self.env['syncops.connector.line.default'].search([
            ('connector_id', '=', connector.id),
            ('name', '=', name),
            ('method', '=', method),
            ('io', '=', io),
        ], limit=1)
        if not default:
            default = self.env['syncops.connector.line.default'].create({
                'connector_id': connector.id,
                'name': name,
                'method': method,
                'io': io,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Set Default'),
            'res_id': default.id,
            'res_model': 'syncops.connector.line.default',
            'context': {'dialog_size': 'small'},
            'view_mode': 'form',
            'target': 'new',
        }


class SyncopsConnectorLineInput(models.Model):
    _name = 'syncops.connector.line.input'
    _inherit = 'syncops.connector.line.io'
    _description = 'syncOPS Connector Line Input'


class SyncopsConnectorLineOutput(models.Model):
    _name = 'syncops.connector.line.output'
    _inherit = 'syncops.connector.line.io'
    _description = 'syncOPS Connector Line Output'


class SyncopsConnectorLineDefault(models.Model):
    _name = 'syncops.connector.line.default'
    _description = 'syncOPS Connector Line Defaults'

    connector_id = fields.Many2one('syncops.connector', ondelete='cascade')
    name = fields.Char()
    method = fields.Char()
    io = fields.Selection([
        ('input', 'Input'),
        ('output', 'Output'),
    ])
    type = fields.Selection([
        ('none', 'None'),
        ('const', 'Constant'),
        ('code', 'Code'),
    ], default='none')
    const = fields.Char()
    code = fields.Text()

    def _value(self, values={}):
        if self.type == 'const':
            return self.const
        elif self.type == 'code':
            context = {
                'env': self.env,
                'datetime': datetime,
                **values
            }
            safe_eval(self.code.strip(), context, mode='exec', nocopy=True)
            return context.get('self')
        return

    @api.constrains('code')
    def _check_code(self):
        for line in self.sudo().filtered('code'):
            msg = test_python_expr(expr=line.code.strip(), mode='exec')
            if msg:
                raise ValidationError(msg)


class SyncopsLog(models.TransientModel):
    _name = 'syncops.log'
    _description = 'syncOPS Logs'
    _order = 'date DESC'

    connector_id = fields.Many2one('syncops.connector', readonly=True, copy=False, index=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', readonly=True, copy=False, ondelete='cascade')
    date = fields.Datetime(string='Date', readonly=True, copy=False)
    partner_name = fields.Char(string='Partner', readonly=True, copy=False)
    connector_name = fields.Char(string='Connector', readonly=True, copy=False)
    token_name = fields.Char(string='Token', readonly=True, copy=False)
    method_name = fields.Char(string='Method', readonly=True, copy=False)
    state = fields.Selection([('error', 'Error'), ('success', 'Success')], string='State', readonly=True, copy=False)
    status = fields.Boolean(string='Success', readonly=True, copy=False)
    message = fields.Text(string='Message', readonly=True, copy=False)
    duration = fields.Float(string='Duration', digits=(16, 2), readonly=True, copy=False)
    request_method = fields.Selection([
        ('post', 'POST'),
        ('get', 'GET'),
        ('put', 'PUT'),
        ('delete', 'DELETE'),
    ], string='Request Method', readonly=True, copy=False)
    request_url = fields.Text(string='Request Url', readonly=True, copy=False)
    request_data = fields.Text(string='Request Data', readonly=True, copy=False)
    response_code = fields.Integer(string='Response Code', readonly=True, copy=False)
    response_message = fields.Char(string='Response Message', readonly=True, copy=False)
    response_data = fields.Text(string='Response Data', readonly=True, copy=False)

    def name_get(self):
        return [(log.id, 'Log #%s' % log.id) for log in self]
