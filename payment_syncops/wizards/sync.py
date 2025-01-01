# -*- coding: utf-8 -*-
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

            self.line_ids = [(0, 0, {
                'name': line.get('name', False),
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
                'partner_iban': line.get('iban', False),
                'partner_tag': line.get('tag', False),
            }) for line in lines]
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

                self.line_ids = [(5, 0, 0)] + [(0, 0, {
                    'name': line.get('name', False),
                    'partner_name': line.get('partner', False),
                    'partner_vat': line.get('vat', False),
                    'partner_ref': line.get('ref', False),
                    'partner_email': line.get('email', False),
                    'partner_phone': line.get('phone', False),
                    'partner_mobile': line.get('mobile', False),
                    'partner_balance': line.get('balance', 0),
                }) for line in lines if float(line.get('balance', 0)) > 0]
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
                self.line_ids = [(5, 0, 0)] + [(0, 0, {
                    'name': line.get('partner', False),
                    'partner_name': line.get('partner', False),
                    'partner_vat': line.get('vat', False),
                    'partner_ref': line.get('ref', False),
                    'partner_email': line.get('email', False),
                    'partner_phone': line.get('phone', False),
                    'partner_mobile': line.get('mobile', False),
                    'invoice_id': line.get('id', False),
                    'invoice_tag': line.get('tag', False),
                    'invoice_name': line.get('name', False),
                    'invoice_date': line.get('date', False),
                    'invoice_due_date': line.get('due_date', False),
                    'invoice_amount': line.get('amount', 0),
                    'invoice_currency': currencies.get(line.get('currency'), False),
                }) for line in lines]
                res['view_id'] = self.env.ref('payment_syncops.tree_wizard_sync_line_item_invoice').id

        return res

    def sync(self):
        res = super().sync()
        self = self.sudo()
        wizard = self.browse(self.env.context.get('wizard_id', 0))
        if wizard:
            company = self.env.company

            users_all = self.env['res.users']
            users = users_all.search_read([
                ('email', 'in', wizard.line_ids.mapped('partner_user_email'))
            ], ['id', 'email'])
            users = {user['email']: user['id'] for user in users if user['email']}

            partners_all = self.env['res.partner']
            partners = partners_all.search_read([
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

            tags = {tag.code: tag.ids for tag in self.env['res.partner.category'].search([('company_id', '=', company.id)])}

            vats, refs = {}, {}
            for partner in partners:
                if partner['vat']:
                    vats.update({partner['vat']: partner['id']})
                if partner['ref']:
                    refs.update({partner['ref']: partner['id']})

            if wizard.type == 'partner':
                for line in wizard.line_ids.read():
                    if line['partner_user_email'] in users:
                        user = users_all.browse(users[line['partner_user_email']])
                        user.with_context(mail_create_nolog=True).write({
                            'name': line['partner_user_name'],
                            'phone': line['partner_user_phone'],
                            'mobile': line['partner_user_mobile'] or line['partner_user_phone'],
                            'company_ids': [(4, company.id)],
                        })
                    elif line['partner_user_email']:
                        user = users_all.sudo().search([
                            ('email', '=', line['partner_user_email']),
                        ], limit=1)
                        if user:
                            user.with_context(mail_create_nolog=True).write({
                                'company_ids': [(4, company.id)],
                            })
                        else:
                            user = users_all.with_context(mail_create_nolog=True).create({
                                'system': wizard.system or company.system,
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
                        partner = partners_all.browse(pid)
                        partner.write({
                            'name': line['name'],
                            'vat': line['partner_vat'],
                            'ref': line['partner_ref'],
                            'email': line['partner_email'],
                            'phone': line['partner_phone'],
                            'mobile': line['partner_mobile'] or line['partner_phone'],
                            'campaign_id': campaigns.get(line['partner_campaign'], False),
                            'category_id': [(6, 0, tags.get(line['partner_tag'], []))],
                            'user_id': user and user.id or partner.user_id.id,
                        })
                    else:
                        values = {
                            'system': wizard.system or company.system,
                            'name': line['name'],
                            'vat': line['partner_vat'],
                            'ref': line['partner_ref'],
                            'email': line['partner_email'],
                            'phone': line['partner_phone'],
                            'mobile': line['partner_mobile'] or line['partner_phone'],
                            'campaign_id': campaigns.get(line['partner_campaign'], False),
                            'category_id': [(6, 0, tags.get(line['partner_tag'], []))],
                            'user_id': user and user.id,
                            'company_id': company.id,
                            'is_company': True,
                        }
                        if line['partner_iban']:
                            values.update({
                                'bank_ids': [(0, 0, {
                                    'acc_number': line['partner_iban'],
                                    'api_merchant': 'HEDEF_FILO_ODEMESI',
                                })]
                            })
                        partner = partners_all.create(values)
                        if line['partner_vat']:
                            vats.update({line['partner_vat']: partner.id})
                        if line['partner_ref']:
                            refs.update({line['partner_ref']: partner.id})

            else:
                items_all = self.env['payment.item']
                if wizard.type_item_subtype == 'balance':
                    items = items_all.search_read([
                        ('paid', '=', False),
                        ('company_id', '=', company.id),
                        ('vat', 'in', wizard.line_ids.mapped('partner_vat')),
                        ('system', '=', wizard.system),
                    ], ['id', 'parent_id'])

                    items = {item['parent_id'][0]: item['id'] for item in items}
                    for line in wizard.line_ids.read():
                        pid = 0
                        if line['partner_vat'] in vats and line['partner_ref'] in refs and vats[line['partner_vat']] == refs[line['partner_ref']]:
                            pid = vats[line['partner_vat']]
                        elif line['partner_vat'] in vats:
                            pid = vats[line['partner_vat']]
                        elif line['partner_ref'] in refs:
                            pid = refs[line['partner_ref']]

                        if pid and pid in items:
                            items_all.browse(items[pid]).write({
                                'amount': line['partner_balance'],
                            })
                        else:
                            if pid:
                                partner = partners_all.browse(pid)
                            else:
                                partner = partners_all.create({
                                    'system': wizard.system or company.system,
                                    'name': line['name'],
                                    'vat': line['partner_vat'],
                                    'ref': line['partner_ref'],
                                    'email': line['partner_email'],
                                    'phone': line['partner_phone'],
                                    'mobile': line['partner_phone'],
                                    'campaign_id': campaigns.get(line['partner_campaign'], False),
                                    'category_id': [(6, 0, tags.get(line['partner_tag'], []))],
                                    'company_id': company.id,
                                    'is_company': True,
                                })
                                if line['partner_vat']:
                                    vats.update({line['partner_vat']: partner.id})
                                if line['partner_ref']:
                                    refs.update({line['partner_ref']: partner.id})

                            items_all.create({
                                'syncops_ok': True,
                                'syncops_notif': self._set_notif(company, partner),
                                'system': wizard.system or company.system,
                                'amount': line['partner_balance'],
                                'parent_id': partner.id,
                                'company_id': company.id,
                                'currency_id': line['currency_id'] and line['currency_id'][0] or company.currency_id.id,
                            })
                elif wizard.type_item_subtype == 'invoice':
                    domain = [
                        ('company_id', '=', company.id),
                        ('system', '=', wizard.system),
                        ('ref', '!=', False),
                    ]
                    partner_ctx = self.env.context.get('partner')
                    if partner_ctx:
                        domain.append(('parent_id', '=', partner_ctx.id))

                    if company.syncops_sync_item_force:
                        items_all.search(domain).unlink()
                    else:
                        items_all.search(domain + [('paid', '=', False), ('ref', 'not in', wizard.line_ids.mapped('invoice_id'))]).unlink()

                    items = items_all.search_read(domain, ['id', 'ref'])
                    items = {item['ref']: item['id'] for item in items if item['ref']}
                    for line in wizard.line_ids.read():
                        pid = 0
                        if line['partner_vat'] in vats and line['partner_ref'] in refs and vats[line['partner_vat']] == refs[line['partner_ref']]:
                            pid = vats[line['partner_vat']]
                        elif line['partner_vat'] in vats:
                            pid = vats[line['partner_vat']]
                        elif line['partner_ref'] in refs:
                            pid = refs[line['partner_ref']]

                        inv = line['invoice_id'] if pid else None
                        if pid and inv in items:
                            items_all.search([('id', '=', items[inv]), ('paid', '=', False)]).write({'amount': line['invoice_amount']})
                        else:
                            if pid:
                                partner = partners_all.browse(pid)
                            else:
                                partner = partners_all.create({
                                    'system': wizard.system or company.system,
                                    'name': line['partner_name'],
                                    'vat': line['partner_vat'],
                                    'ref': line['partner_ref'],
                                    'email': line['partner_email'],
                                    'phone': line['partner_phone'],
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

                            items_all.create({
                                'syncops_ok': True,
                                'syncops_notif': self._set_notif(company, partner),
                                'system': wizard.system or company.system,
                                'amount': line['invoice_amount'],
                                'description': line['invoice_name'],
                                'date': line['invoice_date'],
                                'due_date': line['invoice_due_date'],
                                'ref': line['invoice_id'],
                                'tag': line['invoice_tag'],
                                'parent_id': partner.id,
                                'company_id': company.id,
                                'currency_id': line['invoice_currency'] and line['invoice_currency'][0] or company.currency_id.id,
                            })
        return res


class SyncopsSyncWizardLine(models.TransientModel):
    _inherit = 'syncops.sync.wizard.line'

    partner_id = fields.Char(readonly=True)
    partner_name = fields.Char(readonly=True)
    partner_vat = fields.Char(readonly=True)
    partner_ref = fields.Char(readonly=True)
    partner_tag = fields.Char(readonly=True)
    partner_email = fields.Char(readonly=True)
    partner_phone = fields.Char(readonly=True)
    partner_mobile = fields.Char(readonly=True)
    partner_campaign = fields.Char(readonly=True)
    partner_iban = fields.Char(readonly=True)
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
