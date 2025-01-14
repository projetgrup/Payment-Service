# -*- coding: utf-8 -*-
import requests
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PaymentTransaction(models.Model):
    _name = 'payment.transaction'
    _inherit = ['payment.transaction', 'mail.thread']

    def _compute_item_count(self):
        for tx in self:
            tx.paylox_item_count = len(tx.jetcheckout_item_ids)

    def _compute_jetcheckout_can_export_txt(self):
        for tx in self:
            tx.jetcheckout_can_export_txt = tx.company_id.payment_transaction_export_txt

    state = fields.Selection(tracking=True)
    system = fields.Selection(related='company_id.system')
    partner_ref = fields.Char(string='Partner Reference', related='partner_id.ref')

    paylox_item_count = fields.Integer(compute='_compute_item_count')
    paylox_item_tag_id = fields.Many2one('payment.settings.campaign.tag', 'Payment Item Tag', readonly=True, copy=False)
    paylox_item_tag_name = fields.Char('Payment Item Tag Name', readonly=True, copy=False)
    paylox_item_tag_code = fields.Char('Payment Item Tag Code', readonly=True, copy=False)
    paylox_prepayment_amount = fields.Monetary('Prepayment Amount', readonly=True, copy=False)
    paylox_sale_ref = fields.Char('Sale Reference', readonly=True, copy=False)
    paylox_transaction_item_ids = fields.One2many('payment.transaction.item', 'transaction_id', string='Transaction Items')
    jetcheckout_can_export_txt = fields.Boolean('Can Export TXT', compute='_compute_jetcheckout_can_export_txt')

    jetcheckout_item_ids = fields.Many2many('payment.item', 'transaction_item_rel', 'transaction_id', 'item_id', string='Payment Items')
    jetcheckout_webhook_ok = fields.Boolean('Webhook Notification', readonly=True)
    jetcheckout_webhook_state = fields.Boolean('Webhook Notification State', readonly=True)
    jetcheckout_webhook_state_message = fields.Text('Webhook Notification State Message', readonly=True)
    jetcheckout_webhook_failed_ids = fields.Many2many('payment.settings.notification.webhook', 'transaction_webhook_rel', 'transaction_id', 'webhook_id', string='Failed Webhook Notifications', readonly=True)
    jetcheckout_partner_user_id = fields.Many2one('res.users', 'Sales Representative', related='partner_id.user_id', store=True, readonly=True, ondelete='set null')
    jetcheckout_partner_team_id = fields.Many2one('crm.team', 'Sales Team', related='partner_id.team_id', store=True, readonly=True, ondelete='set null')
    jetcheckout_partner_categ_ids = fields.Many2many('res.partner.category', 'transaction_partner_category_rel', 'transaction_id', 'category_id', 'Tags', related='partner_id.category_id', store=True, readonly=True, ondelete='set null')

    @api.model
    def run_hook(self, subtype, **kwargs):
        hook = self.env['payment.hook'].sudo().search([
            ('type', '=', 'transaction'),
            ('subtype', '=', subtype),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if hook:
            hook.run(**kwargs)

    @api.model
    def create(self, values):
        self.run_hook('create', values=values)
        if values.get('paylox_item_tag_id'):
            tag = self.env['payment.settings.campaign.tag'].sudo().browse(values['paylox_item_tag_id'])
            values['paylox_item_tag_name'] = tag.name
        if values.get('jetcheckout_item_ids'):
            item = self.env['payment.item'].sudo().browse(values['jetcheckout_item_ids'][0][2])
            values['paylox_item_tag_code'] = '/'.join(set([i.tag or '-' for i in item]))
        return super().create(values)

    def action_items(self):
        self.ensure_one()
        system = self.company_id.system or self.partner_id.system or 'jetcheckout_system'
        action = self.env.ref('payment_%s.action_item' % system).sudo().read()[0]
        action['domain'] = [('id', 'in', self.jetcheckout_item_ids.ids)]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        return action

    def action_process_notification_webhook(self):
        self.ensure_one()
        if not self.jetcheckout_webhook_ok or not self.jetcheckout_webhook_state:
            return

        webhooks = self.jetcheckout_webhook_failed_ids
        if not webhooks:
            self.write({
                'jetcheckout_webhook_ok': True,
                'jetcheckout_webhook_state': True,
                'jetcheckout_webhook_state_message': _('This transaction is successfully notified.')
            })
            return

        message = []
        json = self._get_notification_webhook_data()
        for webhook in webhooks:
            try:
                response = requests.post(webhook.url, json=json, timeout=10)
                if response.ok:
                    self.write({'jetcheckout_webhook_failed_ids': [(3, webhook.id, 0)]})
                else:
                    message.append(_('URL %s could not be notified: %s') % (webhook.url, response.reason))

            except Exception as e:
                message.append(_('URL %s could not be notified: %s') % (webhook.url, e))

        if message:
            self.write({
                'jetcheckout_connector_state': True,
                'jetcheckout_connector_state_message': _('This transaction has not been successfully notified.\n%s') % '\n'.join(message)
            })
        else:
            self.write({
                'jetcheckout_connector_state': False,
                'jetcheckout_connector_state_message': _('This transaction has been successfully notified.')
            })

    def action_export_txt(self):
        txs = self.filtered(lambda t: t.jetcheckout_can_export_txt)
        if not txs:
            raise UserError(_('You are not allowed to export transactions as TXT file. Please contact with your administrator.'))
        return {
            'type': 'ir.actions.act_url',
            'url': '/paylox/payment/transactions/txt?=%s' % ','.join(map(str, txs.ids))
        }


    def _get_notification_webhook_data(self):
        return {
            'parent': {
                'name': self.partner_id.name,
                'vat': self.partner_id.vat,
            },
            'items': [{
                'child': {
                    'name': item.child_id.name,
                    'vat': item.child_id.vat,
                    'ref': item.child_id.ref,
                },
                'amount': {
                    'total': item.amount,
                    'discount': {
                        'prepayment': item.prepayment_amount,
                    },
                    'installment': {
                        'count': item.installment_count or 1,
                        'amount': item.paid_amount / (item.installment_count or 1),
                    },
                    'paid': item.paid_amount,
                }
            } for item in self.jetcheckout_item_ids],
            'card': {
                'family': self.jetcheckout_card_family,
                'vpos': self.jetcheckout_vpos_name,
            }
        }

    def _paylox_done_postprocess(self):
        res = super()._paylox_done_postprocess()
        webhooks = self.company_id.notif_webhook_ids
        if webhooks:
            self.write({
                'jetcheckout_webhook_ok': True,
                'jetcheckout_webhook_failed_ids': [(6, 0, webhooks.ids)],
                'jetcheckout_webhook_state': True,
                'jetcheckout_webhook_state_message': _('This transaction has not been notified yet.')
            })
            self.action_process_notification_webhook()
        return res


class PaymentTransactionItem(models.Model):
    _name = 'payment.transaction.item'
    _description = 'Payment Transaction Items'

    transaction_id = fields.Many2one('payment.transaction', required=True, ondelete='cascade')
    item_id = fields.Many2one('payment.item', string='Item')
    ref = fields.Char('Reference')
    date = fields.Date('Date')
    desc = fields.Char('Description')
    advance = fields.Boolean('Advance')
    amount = fields.Monetary('Amount')
    currency_id = fields.Many2one(related='transaction_id.currency_id')

    @api.model
    def create(self, values):
        res = super().create(values)
        if res.advance:
            res.transaction_id.paylox_prepayment_amount = res.amount
        return res