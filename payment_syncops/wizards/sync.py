# -*- coding: utf-8 -*-
import json
from odoo import fields, models, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import UserError, ValidationError


class SyncopsSyncWizard(models.TransientModel):
    _inherit = 'syncops.sync.wizard'

    @api.onchange('type')
    def _compute_type_item_subtype_ok(self):
        for rec in self:
            if rec.type == 'item':
                access_partner_list = self.env['syncops.connector'].count('payment_get_partner_list')
                access_unreconciled_list = self.env['syncops.connector'].count('payment_get_unreconciled_list')
                rec.type_item_subtype_ok = access_partner_list and access_unreconciled_list
            else:
                rec.type_item_subtype_ok = False

    system = fields.Char()
    type_item_date_start = fields.Date()
    type_item_date_end = fields.Date()
    type_item_subtype = fields.Selection([('balance', 'Current Balances'), ('invoice', 'Unpaid Invoices')])
    type_item_subtype_ok = fields.Boolean(compute='_compute_type_item_subtype_ok')

    def _show_options(self):
        res = super()._show_options()
        if self.type == 'partner':
            return False
        elif self.type == 'item':
            return True
        return res

    def _set_notif(self, company, partner):
        if company.syncops_cron_sync_item_notif_ok:
            cids = company.syncops_cron_sync_item_notif_tag_ids.ids
            if company.syncops_cron_sync_item_notif_tag_ok:
                return partner.category_id.id in cids
            else:
                return partner.category_id.id not in cids
        else:
            return False

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res['system'] = self.env.context.get('active_system')

        model = self.env.context.get('active_model')
        if model == 'res.partner':
            res['type'] = 'partner'
        elif model == 'payment.item':
            res['type'] = 'item'
        else:
            res['type'] = False

        if res['type'] == 'item':
            res['type_item_subtype'] = self.env.company.syncops_sync_item_subtype or 'balance'

        return res

    def confirm(self):
        res = super().confirm()
        params = {'company': self.env.company.sudo().partner_id.ref}
        if not self.env.context.get('partner') and self.type == 'partner':
            lines = self.env['syncops.connector']._execute('payment_get_partner_list', params=params)
            if lines == None:
                raise ValidationError(_('An error occured. Please try again.'))
            if not lines:
                lines = []

            methods = {
                'value': lambda line: {
                    'name': line.get('name', False),
                    'data': json.dumps(line, default=str),
                    'partner_vat': line.get('vat', False),
                    'partner_ref': line.get('ref', False),
                    'partner_email': line.get('email', False),
                    'partner_phone': line.get('phone', False),
                    'partner_mobile': line.get('mobile', False),
                    'partner_user_name': line.get('user_name', False),
                    'partner_user_email': line.get('user_email', False),
                    'partner_user_phone': line.get('user_phone', False),
                    'partner_user_mobile': line.get('user_mobile', False),
                    'partner_balance': line.get('balance', 0),
                    'partner_campaign': line.get('campaign', False),
                    'partner_address': line.get('address', False),
                    'partner_tag': line.get('tag', False),
                },
                'filter': lambda line: True,
            }
            hook = self.env['syncops.connector'].get_hook('payment_get_partner_list', 'pre', 'partner')
            if hook:
                hook.run(wizard=self, methods=methods, lines=lines)

            self.line_ids = [(0, 0, methods['value'](line)) for line in lines if methods['filter'](line)]
            res['view_id'] = self.env.ref('payment_syncops.tree_wizard_sync_line_partner').id

        elif self.type == 'item':
            if not self.env.context.get('partner'):
                self.env.cr.execute(f"UPDATE res_company SET syncops_sync_item_subtype='{self.type_item_subtype}' WHERE id={self.env.company.id}")

            if not self.env.context.get('partner') and self.type_item_subtype == 'balance':
                lines = self.env['syncops.connector']._execute('payment_get_partner_list', params=params)
                if lines == None:
                    lines = []

                if self.env.company.syncops_sync_item_no_partner:
                    refs = self.env['res.partner'].sudo().search([
                        ('company_id', '=', self.env.company.id),
                        ('system', '=', self.env.company.system),
                        ('ref', 'not in', ('', False)),
                    ]).mapped('ref')
                    lines = list(filter(lambda l: l.get('ref') in refs, lines))

                methods = {
                    'value': lambda line: {
                        'name': line.get('name', False),
                        'data': json.dumps(line, default=str),
                        'partner_name': line.get('partner', False),
                        'partner_vat': line.get('vat', False),
                        'partner_ref': line.get('ref', False),
                        'partner_email': line.get('email', False),
                        'partner_phone': line.get('phone', False),
                        'partner_mobile': line.get('mobile', False),
                        'partner_address': line.get('address', False),
                        'partner_balance': line.get('balance', 0),
                    },
                    'filter': lambda line: float(line.get('balance', 0)) > 0,
                }
                hook = self.env['syncops.connector'].get_hook('payment_get_partner_list', 'pre', 'item', 'balance')
                if hook:
                    hook.run(wizard=self, methods=methods, lines=lines)

                self.line_ids = [(0, 0, methods['value'](line)) for line in lines if methods['filter'](line)]
                res['view_id'] = self.env.ref('payment_syncops.tree_wizard_sync_line_item_balance').id

            elif self.type_item_subtype == 'invoice':
                if not self.type_item_subtype_ok:
                    raise UserError(_('"Get Unreconciled Records List" method must be activated to get records by their date range'))
                if self.type_item_date_start:
                    params.update({'date_start': self.type_item_date_start.strftime(DF)})
                if self.type_item_date_end:
                    params.update({'date_end': self.type_item_date_end.strftime(DF)})

                lines = self.env['syncops.connector']._execute('payment_get_unreconciled_list', params=params)
                if lines == None:
                    lines = []

                if self.env.company.syncops_sync_item_no_partner:
                    refs = self.env['res.partner'].sudo().search([
                        ('company_id', '=', self.env.company.id),
                        ('system', '=', self.env.company.system),
                        ('ref', 'not in', ('', False)),
                    ]).mapped('ref')
                    lines = list(filter(lambda l: l.get('ref') in refs, lines))

                currencies = self.env['res.currency'].with_context(active_test=False).search_read([], ['id', 'name'])
                currencies = {currency['name']: currency['id'] for currency in currencies}

                methods = {
                    'value': lambda line: {
                        'name': line.get('partner', False),
                        'data': json.dumps(line, default=str),
                        'partner_name': line.get('partner', False),
                        'partner_vat': line.get('vat', False),
                        'partner_ref': line.get('ref', False),
                        'partner_email': line.get('email', False),
                        'partner_phone': line.get('phone', False),
                        'partner_mobile': line.get('mobile', False),
                        'partner_address': line.get('address', False),
                        'invoice_id': line.get('id', False),
                        'invoice_tag': line.get('tag', False),
                        'invoice_name': line.get('name', False),
                        'invoice_date': line.get('date', False),
                        'invoice_due_date': line.get('due_date', False),
                        'invoice_amount': line.get('amount', 0),
                        'invoice_currency': currencies.get(line.get('currency'), False),
                    },
                    'filter': lambda line: True,
                }
                hook = self.env['syncops.connector'].get_hook('payment_get_unreconciled_list', 'pre', 'item', 'invoice')
                if hook:
                    hook.run(wizard=self, methods=methods, currencies=currencies, lines=lines)

                self.line_ids = [(0, 0, methods['value'](line)) for line in lines if methods['filter'](line)]
                res['view_id'] = self.env.ref('payment_syncops.tree_wizard_sync_line_item_invoice').id

        return res

    def _sync_partner(self, **pairs):
        vats = pairs.get('vats')
        refs = pairs.get('refs')
        tags = pairs.get('tags')
        users = pairs.get('users')
        models = pairs.get('models')
        company = pairs.get('company')
        campaigns = pairs.get('campaigns')

        def method_sync():
            for line in self.line_ids.read():
                if line['partner_user_email'] in users:
                    user = self.env['res.users'].browse(users[line['partner_user_email']])
                    user.with_context(mail_create_nolog=True).write({
                        'name': line['partner_user_name'],
                        'phone': line['partner_user_phone'],
                        'mobile': line['partner_user_mobile'] or line['partner_user_phone'],
                        'company_ids': [(4, company.id)],
                    })
                elif line['partner_user_email']:
                    user = models['user'].sudo().search([
                        ('email', '=', line['partner_user_email']),
                    ], limit=1)
                    if user:
                        user.with_context(mail_create_nolog=True).write({
                            'company_ids': [(4, company.id)],
                        })
                    else:
                        user = models['user'].with_context(mail_create_nolog=True).create({
                            'system': self.system or company.system,
                            'name': line['partner_user_name'],
                            'login': line['partner_user_email'],
                            'email': line['partner_user_email'],
                            'phone': line['partner_user_phone'],
                            'mobile': line['partner_user_mobile'] or line['partner_user_phone'],
                            'company_id': company.id,
                            'privilege': 'user',
                        })
                else:
                    user = None

                pid = 0
                if line['partner_vat'] in vats and line['partner_ref'] in refs and vats[line['partner_vat']] == refs[line['partner_ref']]:
                    pid = vats[line['partner_vat']]
                elif line['partner_vat'] in vats:
                    pid = vats[line['partner_vat']]
                elif line['partner_ref'] in refs:
                    pid = refs[line['partner_ref']]

                if pid:
                    partner = models['partner'].browse(pid)
                    partner.write({
                        'name': line['name'],
                        'vat': line['partner_vat'],
                        'ref': line['partner_ref'],
                        'email': line['partner_email'],
                        'phone': line['partner_phone'],
                        'street': line['partner_address'],
                        'mobile': line['partner_mobile'] or line['partner_phone'],
                        'campaign_id': campaigns.get(line['partner_campaign'], False),
                        'category_id': [(6, 0, tags.get(line['partner_tag'], []))],
                        'syncops_data': json.dumps(line['data'], default=str),
                        'user_id': user and user.id or partner.user_id.id,
                    })
                else:
                    values = {
                        'system': self.system or company.system,
                        'name': line['name'],
                        'vat': line['partner_vat'],
                        'ref': line['partner_ref'],
                        'email': line['partner_email'],
                        'phone': line['partner_phone'],
                        'street': line['partner_address'],
                        'mobile': line['partner_mobile'] or line['partner_phone'],
                        'campaign_id': campaigns.get(line['partner_campaign'], False),
                        'category_id': [(6, 0, tags.get(line['partner_tag'], []))],
                        'syncops_data': json.dumps(line['data'], default=str),
                        'user_id': user and user.id,
                        'company_id': company.id,
                        'is_company': True,
                    }
                    partner = models['partner'].create(values)
                    if line['partner_vat']:
                        vats.update({line['partner_vat']: partner.id})
                    if line['partner_ref']:
                        refs.update({line['partner_ref']: partner.id})

        methods = {'sync': method_sync}
        hook = self.env['syncops.connector'].get_hook('payment_get_partner_list', 'post', 'partner')
        if hook:
            hook.run(wizard=self, methods=methods, **pairs)
        methods['sync']()

    def _sync_item_balance(self, **pairs):
        vats = pairs.get('vats')
        refs = pairs.get('refs')
        tags = pairs.get('tags')
        models = pairs.get('models')
        company = pairs.get('company')
        campaigns = pairs.get('campaigns')

        items = models['item'].search_read([
            ('paid', '=', False),
            ('company_id', '=', company.id),
            ('vat', 'in', self.line_ids.mapped('partner_vat')),
            ('system', '=', self.system),
        ], ['id', 'parent_id'])

        items = {item['parent_id'][0]: item['id'] for item in items}

        def method_sync():
            for line in self.line_ids.read():
                pid = 0
                if line['partner_vat'] in vats and line['partner_ref'] in refs and vats[line['partner_vat']] == refs[line['partner_ref']]:
                    pid = vats[line['partner_vat']]
                elif line['partner_vat'] in vats:
                    pid = vats[line['partner_vat']]
                elif line['partner_ref'] in refs:
                    pid = refs[line['partner_ref']]

                if pid and pid in items:
                    models['item'].browse(items[pid]).write({
                        'amount': line['partner_balance'],
                    })
                else:
                    if pid:
                        partner = models['partner'].browse(pid)
                    else:
                        partner = models['partner'].create({
                            'system': self.system or company.system,
                            'name': line['name'],
                            'vat': line['partner_vat'],
                            'ref': line['partner_ref'],
                            'email': line['partner_email'],
                            'phone': line['partner_phone'],
                            'mobile': line['partner_phone'],
                            'street': line['partner_address'],
                            'campaign_id': campaigns.get(line['partner_campaign'], False),
                            'category_id': [(6, 0, tags.get(line['partner_tag'], []))],
                            'company_id': company.id,
                            'is_company': True,
                        })
                        if line['partner_vat']:
                            vats.update({line['partner_vat']: partner.id})
                        if line['partner_ref']:
                            refs.update({line['partner_ref']: partner.id})

                    models['item'].create({
                        'syncops_ok': True,
                        'syncops_data': line['data'],
                        'syncops_notif': self._set_notif(company, partner),
                        'syncops_data': json.dumps(line['data'], default=str),
                        'system': self.system or company.system,
                        'amount': line['partner_balance'],
                        'parent_id': partner.id,
                        'company_id': company.id,
                        'currency_id': line['currency_id'] and line['currency_id'][0] or company.currency_id.id,
                    })

        methods = {'sync': method_sync}
        hook = self.env['syncops.connector'].get_hook('payment_get_partner_list', 'post', 'item', 'balance')
        if hook:
            hook.run(wizard=self, methods=methods, items=items, **pairs)
        methods['sync']()

    def _sync_item_invoice(self, **pairs):
        vats = pairs.get('vats')
        refs = pairs.get('refs')
        tags = pairs.get('tags')
        models = pairs.get('models')
        company = pairs.get('company')
        campaigns = pairs.get('campaigns')

        def method_sync():
            domain = [
                ('company_id', '=', company.id),
                ('system', '=', self.system),
                ('ref', '!=', False),
            ]
            partner_ctx = self.env.context.get('partner')
            if partner_ctx:
                domain.append(('parent_id', '=', partner_ctx.id))

            if company.syncops_sync_item_force:
                models['item'].search(domain).unlink()
            elif not company.syncops_sync_item_soft:
                models['item'].search(domain + [('paid', '=', False), ('ref', 'not in', self.line_ids.mapped('invoice_id'))]).unlink()

            items = models['item'].search_read(domain, ['id', 'ref'])
            items = {item['ref']: item['id'] for item in items if item['ref']}
            for line in self.line_ids:
                pid = 0
                if line['partner_vat'] in vats and line['partner_ref'] in refs and vats[line['partner_vat']] == refs[line['partner_ref']]:
                    pid = vats[line['partner_vat']]
                elif line['partner_vat'] in vats:
                    pid = vats[line['partner_vat']]
                elif line['partner_ref'] in refs:
                    pid = refs[line['partner_ref']]

                inv = line['invoice_id'] if pid else None
                if pid and inv in items:
                    item = models['item'].search([('id', '=', items[inv]), ('paid', '=', False)])
                    item.write({'amount': line['invoice_amount']})
                else:
                    if pid:
                        partner = models['partner'].browse(pid)
                    else:
                        partner = models['partner'].create({
                            'system': self.system or company.system,
                            'name': line['partner_name'],
                            'vat': line['partner_vat'],
                            'ref': line['partner_ref'],
                            'email': line['partner_email'],
                            'phone': line['partner_phone'],
                            'street': line['partner_address'],
                            'mobile': line['partner_mobile'] or line['partner_phone'],
                            'campaign_id': campaigns.get(line['partner_campaign'], False),
                            'category_id': [(6, 0, tags.get(line['partner_tag'], []))],
                            'company_id': company.id,
                            'is_company': True,
                        })
                        if line['partner_vat']:
                            vats.update({line['partner_vat']: partner.id})
                        if line['partner_ref']:
                            refs.update({line['partner_ref']: partner.id})

                    item = models['item'].create({
                        'syncops_ok': True,
                        'syncops_data': line['data'],
                        'syncops_notif': self._set_notif(company, partner),
                        'system': self.system or company.system,
                        'amount': line['invoice_amount'],
                        'description': line['invoice_name'],
                        'date': line['invoice_date'],
                        'due_date': line['invoice_due_date'],
                        'ref': line['invoice_id'],
                        'tag': line['invoice_tag'],
                        'parent_id': partner.id,
                        'company_id': company.id,
                        'currency_id': line['invoice_currency']['id'] or company.currency_id.id,
                    })

                line.item_id = item.id

        methods = {'sync': method_sync}
        hook = self.env['syncops.connector'].get_hook('payment_get_unreconciled_list', 'post', 'item', 'invoice')
        if hook:
            hook.run(wizard=self, methods=methods, **pairs)
        methods['sync']()

    def sync(self):
        res = super().sync()
        self = self.sudo()
        wizard = self.browse(self.env.context.get('wizard_id', 0))
        if wizard:
            company = self.env.company

            users_model = self.env['res.users']
            users = users_model.search_read([
                ('email', 'in', wizard.line_ids.mapped('partner_user_email'))
            ], ['id', 'email'])
            users = {user['email']: user['id'] for user in users if user['email']}

            partners_model = self.env['res.partner']
            partners = partners_model.search_read([
                ('company_id', '=', company.id),
                '|',
                ('vat', 'in', wizard.line_ids.mapped('partner_vat')),
                ('ref', 'in', wizard.line_ids.mapped('partner_ref')),
            ], ['id', 'vat', 'ref'])

            campaigns = {}
            acquirer = self.env['payment.acquirer']._get_acquirer(company=company, providers=['jetcheckout'], limit=1)
            if acquirer:
                campaigns_all = self.env['payment.acquirer.jetcheckout.campaign'].search_read([
                    ('acquirer_id', '=', acquirer.id),
                    ('name', '!=', False),
                ], ['id', 'name'])
                for campaign in campaigns_all:
                    campaigns.update({campaign['name']: campaign['id']})

            tags_model = self.env['res.partner.category']
            tags = {tag.code: tag.ids for tag in tags_model.search([('company_id', '=', company.id)])}

            vats, refs = {}, {}
            for partner in partners:
                if partner['vat']:
                    vats.update({partner['vat']: partner['id']})
                if partner['ref']:
                    refs.update({partner['ref']: partner['id']})

            pairs = {
                'vats': vats,
                'refs': refs,
                'tags': tags,
                'users': users,
                'company': company,
                'campaigns': campaigns,
                'models': {
                    'partner': partners_model,
                    'user': users_model,
                    'tag': tags_model,
                }
            }

            if wizard.type == 'partner':
                wizard._sync_partner(**pairs)

            elif wizard.type == 'item':
                pairs['models']['item'] = self.env['payment.item']
                if wizard.type_item_subtype == 'balance':
                    wizard._sync_item_balance(**pairs)
                elif wizard.type_item_subtype == 'invoice':
                    wizard._sync_item_invoice(**pairs)

        return res


class SyncopsSyncWizardLine(models.TransientModel):
    _inherit = 'syncops.sync.wizard.line'

    item_id = fields.Many2one('payment.item', readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
    partner_name = fields.Char(readonly=True)
    partner_vat = fields.Char(readonly=True)
    partner_ref = fields.Char(readonly=True)
    partner_tag = fields.Char(readonly=True)
    partner_email = fields.Char(readonly=True)
    partner_phone = fields.Char(readonly=True)
    partner_mobile = fields.Char(readonly=True)
    partner_campaign = fields.Char(readonly=True)
    partner_address = fields.Char(readonly=True)
    partner_balance = fields.Monetary(readonly=True)
    partner_user_name = fields.Char(string='Partner Salesperson Name', readonly=True)
    partner_user_email = fields.Char(string='Partner Salesperson Email', readonly=True)
    partner_user_phone = fields.Char(string='Partner Salesperson Phone', readonly=True)
    partner_user_mobile = fields.Char(string='Partner Salesperson Mobile', readonly=True)
    invoice_id = fields.Char(readonly=True)
    invoice_tag = fields.Char(readonly=True)
    invoice_name = fields.Char(readonly=True)
    invoice_date = fields.Date(readonly=True)
    invoice_due_date = fields.Date(readonly=True)
    invoice_amount = fields.Monetary(readonly=True, currency_field='invoice_currency')
    invoice_currency = fields.Many2one('res.currency', readonly=True)
