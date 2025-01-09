# -*- coding: utf-8 -*-
import requests
from datetime import timedelta
from dateutil import parser

from odoo import fields, models, api, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    jetcheckout_connector_ok = fields.Boolean('Connector Transaction', readonly=True)
    jetcheckout_connector_sent = fields.Boolean('Connector Sent', readonly=True)
    jetcheckout_connector_state = fields.Boolean('Connector State', readonly=True)
    jetcheckout_connector_state_message = fields.Text('Connector State Message', readonly=True)
    jetcheckout_connector_payment_ref = fields.Char('Connector Payment Reference', readonly=True)
    jetcheckout_connector_partner_name = fields.Char('Connector Partner Name', readonly=True)
    jetcheckout_connector_partner_vat = fields.Char('Connector Partner VAT', readonly=True)
    jetcheckout_connector_partner_ref = fields.Char('Connector Partner Reference', readonly=True)

    def action_syncops_xlsx(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/syncops/payment/transactions/xlsx?=%s' % ','.join(map(str, self.ids))
        }

    def action_check_connector(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        connector = self.env['syncops.connector'].sudo()._find('payment_post_partner_payment', company=company)
        if not connector:
            raise UserError(_('No syncOPS connector found'))

        if not self.id:
            raise UserError(_('Please save transaction before checking connector logs'))

        result = []
        try:
            url = self.env['ir.config_parameter'].sudo().get_param('syncops.url')
            if not url:
                raise ValidationError(_('No syncOPS endpoint URL found'))

            url += '/api/v1/log'
            response = requests.get(url, params={
                'username': connector.username,
                'token': connector.token,
                'reference': str(self.id),
            })
            if response.status_code == 200:
                results = response.json()
                if not results.get('status') == 0:
                    raise UserError(results['message'])
                logs = results.get('logs', [])
                for log in logs:
                    result.append({
                        'connector_id': connector.id,
                        'company_id': self.env.company.id,
                        'date': parser.parse(log['date']),
                        'partner_name': log['partner'],
                        'connector_name': log['connector'],
                        'token_name': log['token'],
                        'method_name': log['method'],
                        'status': log['status'],
                        'state': log['state'],
                        'message': log['message'],
                        'request_data': log['request_data'],
                        'request_method': log['request_method'],
                        'request_url': log['request_url'],
                        'response_code': log['response_code'],
                        'response_message': log['response_message'],
                        'response_data': log['response_data'],
                    })
            else:
                raise UserError(response.text or response.reason)
        except Exception as e:
            raise UserError(str(e))

        if result:
            logs = self.env['syncops.log'].sudo().create(result)
            action = self.env.ref('connector_syncops.action_log').sudo().read()[0]
            action['context'] = {'create': False, 'delete': False, 'edit': False, 'import': False}
            action['domain'] = [('id', 'in', logs.ids)]
            return action
        else:
            raise UserError(_('No log found'))

    def action_process_connector(self):
        self.ensure_one()
        if not self.jetcheckout_connector_ok or not self.jetcheckout_connector_state:
            return

        if self.source_transaction_id and not self.source_transaction_id.jetcheckout_connector_sent:
            return

        if not self.source_transaction_id and self.state not in ('done', 'cancel'):
            return

        if self.state in self.acquirer_id.syncops_exclude_state_ids.mapped('value'):
            if self.jetcheckout_connector_sent:
                self.write({'jetcheckout_connector_state': False})
            return

        if self.source_transaction_id and self.acquirer_id.syncops_exclude_refund:
            if self.jetcheckout_connector_sent:
                self.write({'jetcheckout_connector_state': False})
            return

        vat = self.jetcheckout_connector_partner_vat or self.partner_id.vat
        ref = self.jetcheckout_connector_partner_ref or self.partner_id.ref
        name = self.jetcheckout_connector_partner_name or self.partner_id.name

        user = self.create_uid
        if user.share and self.partner_id:
            user = self.partner_id.users_id

        line = self.acquirer_id._get_branch_line(name=self.jetcheckout_vpos_name, user=user)
        offset = timedelta(hours=3) # Türkiye Timezone
        date = self.create_date + offset
        if not line or not line.account_code:
            raise UserError(_('There is no account line for this provider'))

        result, message = None, ''
        if self.company_id.syncops_sync_item_split:
            for item in self.paylox_transaction_item_ids:
                 result, message = self.env['syncops.connector'].sudo()._execute('payment_post_partner_payment', reference=str(self.id), params={
                    'id': item.item_id.id,
                    'ref': ref or '',
                    'vat': vat or '',
                    'name': name or '',
                    'tag': self.paylox_item_tag_name or '',
                    'date': date.strftime('%Y-%m-%d %H:%M:%S'),
                    'amount': abs(item.amount),
                    'reference': item.item_id.description or '',
                    'provider': self.acquirer_id.provider,
                    'partner_name': self.partner_id.name,
                    'currency_name': self.currency_id.name,
                    'company_id': self.company_id.partner_id.ref,
                    'account_code': line.account_code,
                    'state': 'refund' if self.source_transaction_id else self.state,
                    'card_number': self.jetcheckout_card_number or '',
                    'card_name': self.jetcheckout_card_name,
                    'order_id': self.source_transaction_id.jetcheckout_order_id if self.source_transaction_id else self.jetcheckout_order_id,
                    'transaction_id': self.source_transaction_id.jetcheckout_transaction_id if self.source_transaction_id else self.jetcheckout_transaction_id,
                    'virtual_pos_id': self.jetcheckout_vpos_id or 0,
                    'virtual_pos_name': self.jetcheckout_vpos_name or '',
                    'installment_count': self.jetcheckout_installment_count or 1,
                    'installment_plus': self.jetcheckout_installment_plus or 0,
                    'installment_code': self.jetcheckout_campaign_name or '',
                    'installments': self.jetcheckout_installment_description or '',
                    'installment_description': self.jetcheckout_installment_description_long or '',
                    'amount_commission_cost': abs(self.jetcheckout_commission_amount or 0),
                    'amount_customer_cost': abs(self.jetcheckout_customer_amount or 0),
                    'amount_commission_rate': abs(self.jetcheckout_commission_rate or 0),
                    'amount_customer_rate': abs(self.jetcheckout_customer_rate or 0),
                    'description': self.state_message or '',
                    'items': [{
                        'ref': item.ref,
                        'amount': float_round(item.amount, 2)
                    }]
                }, company=self.company_id, message=True)
        else:
            result, message = self.env['syncops.connector'].sudo()._execute('payment_post_partner_payment', reference=str(self.id), params={
                'id': self.id,
                'ref': ref or '',
                'vat': vat or '',
                'name': name or '',
                'tag': self.paylox_item_tag_name or '',
                'date': date.strftime('%Y-%m-%d %H:%M:%S'),
                'amount': abs(self.amount),
                'reference': self.reference or '',
                'provider': self.acquirer_id.provider,
                'partner_name': self.partner_id.name,
                'currency_name': self.currency_id.name,
                'company_id': self.company_id.partner_id.ref,
                'account_code': line.account_code,
                'state': 'refund' if self.source_transaction_id else self.state,
                'card_number': self.jetcheckout_card_number or '',
                'card_name': self.jetcheckout_card_name,
                'order_id': self.source_transaction_id.jetcheckout_order_id if self.source_transaction_id else self.jetcheckout_order_id,
                'transaction_id': self.source_transaction_id.jetcheckout_transaction_id if self.source_transaction_id else self.jetcheckout_transaction_id,
                'virtual_pos_id': self.jetcheckout_vpos_id or 0,
                'virtual_pos_name': self.jetcheckout_vpos_name or '',
                'installment_count': self.jetcheckout_installment_count or 1,
                'installment_plus': self.jetcheckout_installment_plus or 0,
                'installment_code': self.jetcheckout_campaign_name or '',
                'installments': self.jetcheckout_installment_description or '',
                'installment_description': self.jetcheckout_installment_description_long or '',
                'amount_commission_cost': abs(self.jetcheckout_commission_amount or 0),
                'amount_customer_cost': abs(self.jetcheckout_customer_amount or 0),
                'amount_commission_rate': abs(self.jetcheckout_commission_rate or 0),
                'amount_customer_rate': abs(self.jetcheckout_customer_rate or 0),
                'description': self.state_message or '',
                'items': [{
                    'ref': item.ref,
                    'amount': float_round(item.amount, 2)
                } for item in self.paylox_transaction_item_ids if item.ref]
            }, company=self.company_id, message=True)

        if result is None:
            self.write({
                'jetcheckout_connector_state': True,
                'jetcheckout_connector_payment_ref': False,
                'jetcheckout_connector_state_message': _('This transaction has not been successfully posted to connector.\n%s') % message
            })
        else:
            values = {
                'jetcheckout_connector_state': False,
                'jetcheckout_connector_payment_ref': result and result[0].get('ref', False) or False,
                'jetcheckout_connector_state_message': _('This transaction has been successfully posted to connector.')
            }
            if not self.source_transaction_id and self.state == 'done':
                values.update({
                    'jetcheckout_connector_sent': True,
                })
            self.write(values)
        self.env.cr.commit()

    def _paylox_done_postprocess(self):
        res = super()._paylox_done_postprocess()
        if self.company_id.syncops_sync_item_force:
            self.env['payment.item'].sudo().search([('parent_id', '=', self.partner_id.id), '|', ('advance', '=', True), ('paid', '=', True)]).unlink()
        if self.jetcheckout_connector_ok:
            self.action_process_connector()
        return res

    def _paylox_cancel_postprocess(self):
        res = super()._paylox_cancel_postprocess()
        if self.jetcheckout_connector_ok:
            self.write({'jetcheckout_connector_state': True})
            self.action_process_connector()
        return res

    def _paylox_refund_postprocess(self, amount=0):
        res = super()._paylox_refund_postprocess(amount=amount)
        if self.jetcheckout_connector_ok:
            res.write({'jetcheckout_connector_ok': True, 'jetcheckout_connector_state': True})
            res.action_process_connector()
        return res

    @api.model
    def create(self, values):
        if values.get('jetcheckout_connector_ok'):
            values['jetcheckout_connector_state'] = True
        res = super().create(values)
        if 'jetcheckout_connector_partner_name' in values:
            res.write({'partner_name': values['jetcheckout_connector_partner_name']})
        return res
