# -*- coding: utf-8 -*-
import base64
import xlrd

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PaymentItemImport(models.TransientModel):
    _name = 'payment.item.import'
    _description = 'Payment Item Import'

    file = fields.Binary()
    filename = fields.Char()
    line_ids = fields.One2many('payment.item.import.line', 'wizard_id', 'Lines', readonly=True)

    def _get_row(self, value):
        return {
            'partner_id': self.env['res.partner'].search([('name', '=', value['Partner'])], limit=1).id,
            'amount': float(value['Amount']),
            'state': value['Status'],
            'state_message': 'Message' in value and value['Message'],
        }

    def _prepare_row(self, line):
        return {
            'acquirer_id': line.acquirer_id.id,
            'partner_id': line.partner_id.id,
            'amount': line.amount,
            'fees': line.fees,
            'jetcheckout_payment_amount': line.amount - line.cost,
            'currency_id': line.currency_id.id,
            'company_id': line.company_id.id,
            'state': line.state,
            'state_message': line.state_message,
            'is_post_processed': True,
        }

    @api.onchange('file')
    def onchange_file(self):
        if self.file:
            data = base64.b64decode(self.file)
            wb = xlrd.open_workbook(file_contents=data)
            sheet = wb.sheet_by_index(0)
            values = []
            cols = []
            for i in range(sheet.nrows):
                row = sheet.row_values(i)
                if not i:
                    cols = row
                    if not 'Partner' in cols:
                        raise UserError(_('Please create a "Partner" column'))
                    elif not 'Amount' in cols:
                        raise UserError(_('Please create a "Amount" column'))
                    elif not 'Status' in cols:
                        raise UserError(_('Please create a "Status" column'))
                else:
                    val = dict(zip(cols, row))
                    if val['Status'] not in ['draft', 'pending', 'authorized', 'done', 'cancel', 'expired', 'error']:
                        raise UserError(_('Status must be one of the following options for row %s:\n%s') % (i+1, 'draft, pending, authorized, done, cancel, expired, error'))

                    vals = self._get_row(val)
                    if 'Currency' in val:
                        vals['currency_id'] = self.env['res.currency'].search([('name', '=', val['Currency'])], limit=1).id
                    if 'Company' in val:
                        vals['company_id'] = self.env['res.company'].search([('name', '=', val['Company'])], limit=1).id
                    if 'Acquirer' in val:
                        vals['acquirer_id'] = self.env['payment.acquirer'].search([('name', '=', val['Acquirer'])], limit=1).id
                    else:
                        vals['acquirer_id'] = self.env['payment.acquirer'].search([('provider', '=', 'jetcheckout')], limit=1).id

                    values.append(vals)
            self.line_ids = [(5, 0, 0)] + [(0, 0, value) for value in values]

        else:
            self.line_ids = [(5, 0, 0)]

    def confirm(self):
        items = self.env['payment.item']
        for line in self.line_ids:
            row = self._prepare_row(line)
            items.create(row)


class PaymentItemImportLine(models.TransientModel):
    _name = 'payment.item.import.line'
    _description = 'Payment Item Import Line'

    wizard_id = fields.Many2one('payment.item.import')
    partner_id = fields.Many2one('res.partner', readonly=True, required=True)
    acquirer_id = fields.Many2one('payment.acquirer', readonly=True, required=True)
    amount = fields.Monetary(readonly=True)
    fees = fields.Monetary(readonly=True)
    cost = fields.Monetary(readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True, required=True, default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', readonly=True, required=True, default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('done', 'Confirmed'),
        ('cancel', 'Canceled'),
        ('expired', 'Expired'),
        ('error', 'Error')
    ], string='Status', default='draft', readonly=True, required=True)
    state_message = fields.Text(string='Message', readonly=True)
