# -*- coding: utf-8 -*-
import json
import requests

from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class PaymentPlan(models.Model):
    _name = 'payment.plan'
    _description = 'Payment Plans'
    _order = 'date desc, id'

    def _compute_name(self):
        for payment in self:
            payment.name = payment.partner_id.name

    @api.depends('paid', 'message')    
    def _compute_result(self):
        for plan in self:
            if plan.paid and plan.message:
                plan.result = '<i class="fa fa-check text-primary" title="%s"/>' % plan.message
            elif plan.message:
                plan.result = '<i class="fa fa-times text-danger" title="%s"/>' % plan.message
            else:
                #plan.result = '<i class="fa fa-minus text-muted" title="%s"/>' % _('No message yet')
                plan.result = ''

    @api.depends('transaction_ids.state')    
    def _compute_paid(self):
        for plan in self:
            transactions = plan.transaction_ids.filtered(lambda tx: tx.state == 'done' and not tx.source_transaction_id)
            for transaction in transactions:
                sources = self.sudo().search([('source_transaction_id', '=', transaction.id)])
                refund_amount = -sum(sources.mapped('amount'))
                if float_compare(refund_amount, transaction.amount, precision_rounding=transaction.currency_id.rounding):
                    continue
                plan.paid = True
                plan.paid_date = transaction.last_state_change
                plan.message = transaction.state_message
                plan.amount_paid = transaction.jetcheckout_payment_paid
                plan.amount_cost = transaction.jetcheckout_commission_amount
                break
            else:
                plan.paid = False
                plan.paid_date = False
                plan.message = False
                plan.amount_paid = False
                plan.amount_cost = False

    name = fields.Char(compute='_compute_name')
    item_id = fields.Many2one('payment.item', ondelete='restrict', readonly=True)
    partner_id = fields.Many2one('res.partner', ondelete='restrict', readonly=True)
    token_id = fields.Many2one('payment.token', ondelete='restrict', readonly=True, string='Credit Card')
    amount = fields.Monetary(readonly=True)
    date = fields.Date(readonly=True)
    result = fields.Html(sanitize=False, readonly=True, compute='_compute_result')
    message = fields.Char(readonly=True, compute='_compute_paid', store=True)
    paid = fields.Boolean(readonly=True, compute='_compute_paid', store=True)
    paid_date = fields.Datetime(readonly=True, compute='_compute_paid', store=True)
    amount_paid = fields.Monetary(readonly=True, compute='_compute_paid', store=True, string='Paid Amount')
    amount_cost = fields.Monetary(readonly=True, compute='_compute_paid', store=True, string='Cost Amount')
    installment_count = fields.Integer(readonly=True, default=1)
    transaction_ids = fields.Many2many('payment.transaction', 'transaction_plan_rel', 'plan_id', 'transaction_id', string='Transactions', readonly=True, ondelete='restrict')
    system = fields.Selection(related='item_id.system', readonly=True, store=True)
    company_id = fields.Many2one(related='item_id.company_id', readonly=True, store=True)
    currency_id = fields.Many2one(related='item_id.currency_id', readonly=True, store=True)
    approval_state = fields.Selection([('+', 'Approved'), ('-', 'Disapproved')], readonly=True)
    approval_result = fields.Char(readonly=True)

    def payment(self):
        if self.paid:
            return

        company = self.partner_id.company_id or self.env.company
        acquirer = self.env['payment.acquirer'].sudo()._get_acquirer(company=company, providers=['jetcheckout'], limit=1, raise_exception=False)
        if not acquirer:
            self.message = _('No acquirer found')
            return

        website = self.env['website'].sudo().search([('company_id', '=', company.id)])
        if not website:
            self.message = _('No website found')
            return

        reference = self.item_id.bank_ref
        if not reference:
            self.message = _('Partner must have at least one bank account which is verified.' % self.partner_id.name)
            return

        if self.installment_count < 1:
            self.installment_count = 1
        installment = self.installment_count

        data = {
            'type': 'virtual_pos',
            'payment': False,
            'threed': False,
            'card': {
                'type': self.token_id.jetcheckout_type or '',
                'program': self.token_id.jetcheckout_program or '',
                'family': self.token_id.jetcheckout_family or '',
                'code': self.token_id.jetcheckout_security or '',
                'date': self.token_id.jetcheckout_expiry or '',
                'holder': self.token_id.jetcheckout_holder or '',
                'token': self.token_id.id or 0,
            },
            'amount': self.amount,
            'item': self.item_id,
            'token': self.token_id,
            'partner': self.partner_id,
            'currency': self.currency_id,
            'website': website,
            'installment': {
                'id': installment,
                'index': 0,
                'rows': [{
                    'id': installment,
                    'count': installment,
                    'plus': 0,
                    'irate': 0.0,
                    'crate': 0.0,
                    'corate': 0.0,
                    'idesc': _('%s Installment') % installment if installment > 1 else _('Single Payment'),
                }],
            },
            'request': {
                'address': '',
                'referrer': '',
            },
            'submerchant': {
                'ref': reference,
                'price': self.amount,
            },
            'campaign': '',
        }

        result = acquirer.action_payment(options={'simulate': True}, **data)
        if result.get('ok'):
            self.write({'transaction_ids': [(4, result['id'])]})
        else:
            self.message = result.get('message') or result.get('error') or _('An error occured')

    def approve(self):
        if self.approval_state == '+':
            return

        transactions = self.transaction_ids.filtered(lambda tx: tx.state == 'done')
        if not transactions:
            self.approval_result = _('Only paid transactions can be approved')
            return

        transaction = transactions[0]
        url = '%s/api/v1/payment/submerchant/approve' % transaction.acquirer_id._get_paylox_api_url()
        data = {
            "application_key": transaction.acquirer_id.jetcheckout_api_key,
            "transaction_id": transaction.jetcheckout_transaction_id,
            "language": "tr",
        }

        response = requests.post(url, data=json.dumps(data))
        try:
            if response.status_code == 200:
                result = response.json()
                if result['response_code'] == "00":
                    self.approval_state = '+'
                    self.approval_result = _('Approved')
                else:
                    self.approval_result = _('%s (Error Code: %s)') % (result['message'], result['response_code'])
            else:
                self.approval_result = _('%s (Error Code: %s)') % (response.reason, response.status_code)
            self.env.cr.commit()
        except:
            self.env.cr.rollback()

    def disapprove(self):
        if self.approval_state == '-':
            return

        transactions = self.transaction_ids.filtered(lambda tx: tx.state == 'done')
        if not transactions:
            return

        transaction = transactions[0]
        url = '%s/api/v1/payment/submerchant/disapprove' % transaction.acquirer_id._get_paylox_api_url()
        data = {
            "application_key": transaction.acquirer_id.jetcheckout_api_key,
            "transaction_id": transaction.jetcheckout_transaction_id,
            "language": "tr",
        }

        response = requests.post(url, data=json.dumps(data))
        try:
            if response.status_code == 200:
                result = response.json()
                if result['response_code'] == "00":
                    self.approval_state = '-'
                    self.approval_result = _('Disapproved')
                else:
                    self.approval_result = _('%s (Error Code: %s)') % (result['message'], result['response_code'])
            else:
                self.approval_result = _('%s (Error Code: %s)') % (response.reason, response.status_code)
            self.env.cr.commit()
        except:
            self.env.cr.rollback()

    def action_payment(self):
        for plan in self:
            plan.payment()

    def action_approve(self):
        for plan in self:
            plan.approve()

    def action_disapprove(self):
        for plan in self:
            plan.disapprove()

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

    def unlink(self):
        for plan in self:
            if plan.paid:
                raise UserError(_('Paid payment plans cannot be deleted'))
        return super().unlink()


class PaymentPlanWizard(models.TransientModel):
    _name = 'payment.plan.wizard'
    _description = 'Payment Plan Wizard'

    @api.depends('item_ids')
    def _compute_desc(self):
        for wizard in self:
            count = len(wizard.item_ids)
            currency = self.env.company.currency_id
            amount = formatLang(self.env, sum(wizard.item_ids.mapped('amount')) - sum(wizard.item_ids.mapped('planned_amount')), currency_obj=currency)
            wizard.desc = _('<strong class="text-primary">%s</strong> partner(s) selected. Total amount is <strong class="text-primary">%s</strong>.' % (count, amount))

    item_ids = fields.Many2many('payment.item', 'item_plan_wizard_rel', 'wizard_id', 'item_id', string='Items', readonly=True)
    desc = fields.Html(sanitize=False, compute='_compute_desc')
    line_ids = fields.One2many('payment.plan.wizard.line', 'wizard_id', string='Lines')

    def action_confirm(self):
        values = []
        lines = [[line.token_id.id, line.token_limit_card, line.token_limit_tx] for line in self.line_ids]
        for item in self.item_ids:
            amount = item.amount - item.planned_amount
            for line in lines:
                while line[1] > 0 and amount > 0:
                    if line[2] > amount:
                        line_amount = amount
                    elif line[1] > line[2]:
                        line_amount = line[2]
                    else:
                        line_amount = line[1]
                    values.append({
                        'date': item.date,
                        'item_id': item.id,
                        'partner_id': item.parent_id.id,
                        'amount': line_amount,
                        'token_id': line[0],
                    })
                    line[1] -= line_amount
                    amount -= line_amount
                if not amount > 0:
                    break

        plans = self.env['payment.plan'].create(values)
        action = self.env.ref('payment_jetcheckout_system.action_plan').sudo().read()[0]
        action['domain'] = [('id', 'in', plans.ids)]
        return action


class PaymentPlanWizardLine(models.TransientModel):
    _name = 'payment.plan.wizard.line'
    _description = 'Payment Plan Wizard Line'

    wizard_id = fields.Many2one('payment.plan.wizard')
    token_id = fields.Many2one('payment.token', string='Credit Card', domain=[('verified', '=', True)], required=True)
    token_limit_card = fields.Float(string='Card Limit')
    token_limit_tx = fields.Float(string='Transaction Limit')

    @api.constrains('token_limit_tx')
    def check_token_limit_tx(self):
        for line in self:
            if not line.token_limit_tx > 0:
                raise UserError(_('Transaction limit must be higher than zero!'))

    @api.onchange('token_id')
    def onchange_token_id(self):
        self.token_limit_card = self.token_id.jetcheckout_limit_card if self.token_id else 0
        self.token_limit_tx = self.token_id.jetcheckout_limit_tx if self.token_id else 0


class PaymentPlanErrorWizard(models.TransientModel):
    _name = 'payment.plan.error.wizard'
    _description = 'Payment Plan Error Wizard'

    item_ids = fields.Many2many('payment.item', 'item_plan_error_wizard_rel', 'wizard_id', 'item_id', string='Items', readonly=True)
