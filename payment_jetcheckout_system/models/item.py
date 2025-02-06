# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.tools.misc import get_lang
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class PaymentItem(models.Model):
    _name = 'payment.item'
    _description = 'Payment Items'
    _order = 'id desc'

    def _compute_name(self):
        for payment in self:
            payment.name = payment.parent_id.name

    def _compute_is_admin(self):
        is_admin = self.env.user.has_group('base.group_system')
        for payment in self:
            payment.is_admin = is_admin

    @api.onchange('child_id')
    def _onchange_child_id(self):
        self.parent_id = self.child_id.parent_id.id if self.child_id else False

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        self.child_id = self.parent_id.child_ids and self.parent_id.child_ids[0].id if self.parent_id else False

    @api.depends('residual_amount')
    def _compute_paid(self):
        for item in self:
            #transactions = item.transaction_ids.filtered(lambda x: x.state == 'done')
            if item.residual_amount:
                item.paid = False
                item.paid_date = False
                item.installment_count = False
            else:
                item.paid = True
                #transaction = transactions[0]
                item.paid_date = fields.Datetime.now() #transaction.last_state_change
                item.installment_count = 1 #transaction.jetcheckout_installment_count
                #item.send_done_mail()

    @api.depends('transaction_ids.state')
    def _compute_paid_amount(self):
        for item in self:
            items = self.env['payment.transaction.item'].sudo().search([
                ('item_id', '=', item.id),
                ('transaction_id.state', '=', 'done'),
            ])
            amount = item.amount
            paid = sum(items.mapped('amount'))
            item.paid_amount = amount if abs(paid) > abs(amount) else paid

    @api.depends('amount', 'paid_amount')
    def _compute_residual_amount(self):
        for item in self:
            item.residual_amount = item.amount - item.paid_amount

    @api.depends('amount', 'date', 'due_date')
    def _compute_due_amount(self):
        today = fields.Date.today()
        base = self.env.company.payment_page_due_base
        for item in self:
            date = item.date if base == 'date_document' else item.due_date
            diff = date - today
            item.due_amount = item.amount * diff.days

    @api.depends('plan_ids.amount')
    def _compute_planned_amount(self):
        for item in self:
            item.planned_amount = sum(item.plan_ids.mapped('amount'))

    @api.depends('date_expire')
    def _compute_date_expired(self):
        now = fields.Datetime.now()
        for item in self:
            item.date_expired = item.company_id.payment_page_item_expire_ok and item.date_expire and now > item.date_expire

    @api.depends('amount', 'planned_amount')
    def _compute_plan_exist(self):
        for item in self:
            item.plan_exist = float_compare(item.amount, item.planned_amount, precision_rounding=item.currency_id.rounding) <= 0

    @api.depends('parent_id.bank_ids.api_state')
    def _compute_plan_iban_exist(self):
        for item in self:
            item.plan_iban_exist = bool(item.bank_ref)

    def _compute_plan_error(self):
        for item in self:
            if not item.paid and not item.plan_iban_exist:
                item.plan_error = '<i class="fa fa-times text-danger" title="%s"/>' % _('IBAN has not been set')
            else:
                item.plan_error = False

    @api.depends('plan_ids.approval_state')
    def _compute_planned(self):
        for item in self:
            item.planned = item.plan_ids and all(plan.approval_state == '+' for plan in item.plan_ids) or False

    def _compute_bank_ref(self):
        for item in self:
            if item.company_id.payment_item_bank_token_ok:
                item.bank_ref = item.bank_token_id.api_state and item.bank_token_id.api_ref
            else:
                bank = item.parent_id.bank_ids and item.parent_id.bank_ids[0]
                item.bank_ref = bank and bank.api_state and bank.api_ref

    name = fields.Char(compute='_compute_name')
    child_id = fields.Many2one('res.partner', ondelete='restrict')
    parent_id = fields.Many2one('res.partner', ondelete='restrict')
    vat = fields.Char(related='parent_id.vat', string='VAT', store=True)
    parent_ref = fields.Char(related='parent_id.ref', string='Partner Reference')
    campaign_id = fields.Many2one(related='parent_id.campaign_id', string='Campaign')

    amount = fields.Monetary()
    advance = fields.Boolean()
    date = fields.Date()
    date_expire = fields.Datetime(string='Expiration Date', readonly=True)
    date_expired = fields.Boolean(string='Expiration Date Passed', compute='_compute_date_expired')
    due_date = fields.Date()
    due_amount = fields.Float(compute='_compute_due_amount')

    ref = fields.Char('Reference', readonly=True)
    tag = fields.Char(readonly=True)
    file = fields.Binary()
    description = fields.Char()
    manual = fields.Boolean()

    paid = fields.Boolean(compute='_compute_paid', store=True, readonly=True)
    paid_amount = fields.Monetary(compute='_compute_paid_amount', store=True, readonly=True)
    planned_amount = fields.Monetary(compute='_compute_planned_amount', store=True, readonly=True)
    residual_amount = fields.Monetary(compute='_compute_residual_amount', store=True, readonly=True)
    installment_count = fields.Integer(compute='_compute_paid', store=True, readonly=True)
    paid_date = fields.Datetime(compute='_compute_paid', store=True, readonly=True)
    is_admin = fields.Boolean(compute='_compute_is_admin')

    planned = fields.Boolean(compute='_compute_planned', store=True, readonly=True)
    plan_ids = fields.One2many('payment.plan', 'item_id', string='Payment Plans')
    plan_error = fields.Html('Plan Error', sanitize=False, compute='_compute_plan_error')
    plan_exist = fields.Boolean('Plan Exist', compute='_compute_plan_exist', store=True)
    plan_iban_exist = fields.Boolean('IBAN Exist', compute='_compute_plan_iban_exist', store=True)
    transaction_item_ids = fields.One2many('payment.transaction.item', 'item_id', string='Transaction Items')
    transaction_ids = fields.Many2many('payment.transaction', 'transaction_item_rel', 'item_id', 'transaction_id', string='Transactions')
    system = fields.Selection(selection=[], readonly=True)
    bank_id = fields.Many2one('res.partner.bank')
    bank_ref = fields.Char('Bank Reference', compute='_compute_bank_ref')
    bank_token_id = fields.Many2one('res.partner.bank.token')
    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', default=lambda self: self.env.company, readonly=True)
    currency_id = fields.Many2one('res.currency', required=True, ondelete='restrict', default=lambda self: self.env.company.currency_id)

    mail_ok = fields.Boolean(readonly=True)
    mail_sent = fields.Boolean(readonly=True)

    def onchange(self, values, field_name, field_onchange):
        return super(PaymentItem, self.with_context(recursive_onchanges=False)).onchange(values, field_name, field_onchange)

    def run_hook(self, subtype, **kwargs):
        hook = self.env['payment.hook'].sudo().search([
            ('type', '=', 'item'),
            ('subtype', '=', subtype),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if hook:
            hook.run(item=self, **kwargs)

    def action_plan(self):
        action = self.env.ref('payment_jetcheckout_system.action_plan').sudo().read()[0]
        action['domain'] = [('id', 'in', self.plan_ids.ids)]
        return action

    def action_plan_wizard(self):
        error_ids = []
        for item in self:
            if item.plan_exist or not item.plan_iban_exist:
                error_ids.append(item.id)

        if error_ids:
            action = self.env.ref('payment_jetcheckout_system.action_plan_error_wizard').sudo().read()[0]
            action['context'] = {'default_item_ids': [(6, 0, error_ids)]}
            return action

        action = self.env.ref('payment_jetcheckout_system.action_plan_wizard').sudo().read()[0]
        context = {'default_item_ids': [(6, 0, self.ids)]}
        token = self.env['payment.token'].search([('company_id', '=', self.env.company.id), ('verified', '=', True)], limit=1)
        if token:
            context.update({
                'default_line_ids': [(0, 0, {
                    'token_id': token.id,
                    'token_limit_card': token.jetcheckout_limit_card,
                    'token_limit_tx': token.jetcheckout_limit_tx,
                })],
            })
        action['context'] = context
        return action

    def action_transaction(self):
        self.ensure_one()
        action = self.env.ref('payment.action_payment_transaction').sudo().read()[0]
        action['domain'] = [('id', 'in', self.transaction_ids.ids)]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        return action

    def action_receipt(self):
        self.ensure_one()
        transaction_ids = self.transaction_ids.filtered(lambda x: x.state == 'done')
        action = self.env.ref('payment_jetcheckout.report_receipt').report_action(transaction_ids.ids)
        return action

    def action_conveyance(self):
        self.ensure_one()
        transaction_ids = self.transaction_ids.filtered(lambda x: x.state == 'done')
        action = self.env.ref('payment_jetcheckout.report_conveyance').report_action(transaction_ids.ids)
        return action

    def action_partner(self):
        self.ensure_one()
        action = self.env.ref('payment_%s.action_parent' % self.system).read()[0]
        action['res_id'] = self.parent_id.id
        action['views'] = [(False, 'form')]
        return action

    @api.model
    def default_get(self, field):
        res = super().default_get(field)
        res['date'] = fields.Date.today()
        res['due_date'] = fields.Date.today()
        return res

    @api.model
    def create(self, values):
        if 'bank_token_id' in values and 'bank_id' not in values:
            token = self.bank_token_id.browse(values['bank_token_id'])
            values.update({'bank_id': token.partner_bank_id.id})
        res = super().create(values)
        if not res.system:
            res.system = res.company_id.system or res.parent_id.system or res.child_id.system
        if not res.currency_id:
            res.currency_id = res.company_id.currency_id.id
        if res.company_id.payment_page_item_expire_ok:
            res.date_expire = fields.Datetime.now() + relativedelta(**{res.company_id.payment_page_item_expire_period: res.company_id.payment_page_item_expire_value})
        res.run_hook('create')
        return res

    def write(self, values):
        if 'bank_token_id' in values and 'bank_id' not in values:
            token = self.bank_token_id.browse(values['bank_token_id'])
            values.update({'bank_id': token.partner_bank_id.id})
        res = super().write(values)
        for item in self:
            if not item.system:
                item.system = item.company_id.system or item.parent_id.system or item.child_id.system
            if not item.currency_id:
                item.currency_id = item.company_id.currency_id.id
        return res

    def _write(self, values):
        res = super()._write(values)
        if values.get('paid'):
            for item in self:
                item.run_hook('finalize')
        return res

    def get_due(self):
        values = {
            'amount': 0.0,
            'days': 0,
            'date': False,
            'campaign': '',
            'advance_amount': 0.0,
            'advance_campaign': '',
            'hide_payment': False,
            'hide_payment_message': '',
        }

        company = self.env.company
        if company.payment_page_due_ok:
            tag = self.env.context.get('tag')
            if tag:
                tag = company.payment_page_campaign_tag_ids.filtered(lambda t: t.id == tag)
                if tag.campaign_id:
                    values.update({
                        'campaign': tag.campaign_id.name,
                    })
                    return values

            amount = 0
            advance_amount = 0
            advance_campaign = ''
            hide_payment = False
            hide_payment_message = ''

            self = self.filtered(lambda x: not x.paid)
            amounts = self.env.context.get('amounts', {})
            total = 0
            for item in self:
                if item.residual_amount < 0:
                    continue
                total += amounts.get(item.id, item.residual_amount)

            today = fields.Date.today()
            lang = get_lang(self.env)
            base = company.payment_page_due_base
            sign = -1 if base == 'date_document' else 1
            for item in self:
                if item.residual_amount < 0:
                    continue
                date = item.due_date if sign == 1 else item.date
                if not date:
                    date = today
                diff = date - today
                residual = amounts.get(item.id, item.residual_amount)
                amount += residual * diff.days

            days = amount/total if total else 0
            date = (today + timedelta(days=days)).strftime(lang.date_format)
            days, campaign, line, advance, hide_payment = company.payment_page_due_ids.get_campaign(days * sign)

            if hide_payment:
                hide_payment_message = company.payment_page_due_hide_payment_message

            if advance:
                due = advance.due + advance.tolerance
                if advance.round:
                    due -= 0.49
                advance_amount = (sign * amount / due) - total if due else 0
                advance_campaign = advance.campaign_id.name

            if self.env.context.get('show_extra'):
                values.update({'line': line})

            values.update({
                'amount': amount,
                'days': days,
                'date': date,
                'campaign': campaign,
                'advance_amount': advance_amount or 0.0,
                'advance_campaign': advance_campaign or '',
                'hide_payment': hide_payment or False,
                'hide_payment_message': hide_payment_message or '',
            })

        return values

    def send_done_mail(self):
        pass

    @api.model
    def paylox_send_due_reminder(self):
        companies = self.env['res.company'].search([
            #('system', '!=', False),
            ('payment_page_due_ok', '!=', False),
            ('payment_page_due_reminder_ok', '!=', False),
        ])
        for company in companies:
            users = company.payment_page_due_reminder_user_ids
            teams = company.payment_page_due_reminder_team_ids
            partners = company.payment_page_due_reminder_partner_ids
            tags = company.payment_page_due_reminder_tag_ids

            domain = [('company_id', '=', company.id), ('paid', '=', False)]
            if users:
                domain.append(('parent_id.user_id', 'in' if company.payment_page_due_reminder_user_ok else 'not in', users.ids))
            if teams:
                domain.append(('parent_id.team_id', 'in' if company.payment_page_due_reminder_team_ok else 'not in', teams.ids))
            if partners:
                domain.append(('parent_id.id', 'in' if company.payment_page_due_reminder_partner_ok else 'not in', partners.ids))
            if tags:
                domain.append(('parent_id.category_id', 'in' if company.payment_page_due_reminder_tag_ok else 'not in', users.ids))

            items = self.env['payment.item'].read_group(domain, ['ids:array_agg(id)'], ['parent_id'])
            for item in items:
                due = self.browse(item['ids']).with_context(show_extra=True).get_due()
                line = due['line']
                if line and line.mail_template_id:
                    if line.due + line.tolerance + 1 - company.payment_page_due_reminder_day == due['days']:
                        partner = self.env['res.partner'].browse(item['parent_id'][0])
                        mail_server = company.mail_server_id
                        email_from = mail_server.email_formatted or company.email_formatted

                        context = self.env.context.copy()
                        context.update({
                            'due': due,
                            'partner': partner,
                            'company': company,
                            'server': mail_server,
                            'from': email_from,
                        })

                        try:
                            with self.env.cr.savepoint():
                                line.mail_template_id.with_context(context).send_mail(partner.id, force_send=True, email_values={
                                    'is_notification': True,
                                    'mail_server_id': mail_server.id,
                                })
                        except Exception as e:
                            _logger.error('An error occured when sending payment due date email to partner %s (%s)' % (partner.id, e))
