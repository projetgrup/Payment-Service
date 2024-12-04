# -*- coding: utf-8 -*-
import base64
import xlrd
from datetime import datetime

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PaymentItemImport(models.TransientModel):
    _name = 'payment.item.import'
    _description = 'Payment Item Import'

    file = fields.Binary()
    filename = fields.Char()
    line_ids = fields.One2many('payment.item.import.line', 'wizard_id', 'Lines', readonly=True)

    def _get_date(self, value):
        if value:
            try:
                return datetime.strptime(value, '%Y-%m-%d')
            except:
                return datetime(*xlrd.xldate_as_tuple(value, 0))
        return value

    def _get_row(self, value):
        return {
            'partner_name': value['Partner Name'],
            'partner_vat': value['Partner VAT'],
            'partner_email': value['Partner Email'],
            'partner_street': value.get('Partner Street', False),
            'partner_tax_office': value.get('Partner Tax Office', False),
            'amount': float(value['Amount']),
            'date': self._get_date(value.get('Date', False)),
            'due_date': self._get_date(value.get('Due Date', False)),
            'ref': value.get('Reference', False),
            'tag': value.get('Tag', False),
            'bank_iban': value.get('Bank IBAN', False),
            'bank_merchant': value.get('Bank Merchant Name', False),
            'description': value.get('Description', False),
            'user_name': value.get('Sales Representative Name', False),
            'user_email': value.get('Sales Representative Email', False),
            'user_mobile': value.get('Sales Representative Mobile', False),
        }

    def _prepare_row(self, line):
        partner = self.env['res.partner'].search([('vat', '=', line.partner_vat), ('company_id', '=', line.company_id.id)], limit=1)
        if partner:
            partner.write({
                'vat': line.partner_vat,
                'street': line.partner_street,
                'paylox_tax_office': line.partner_tax_office,
                'email': line.partner_email,
                'system': line.company_id.system,
            })
        else:
            partner = partner.create({
                'name': line.partner_name,
                'vat': line.partner_vat,
                'street': line.partner_street,
                'paylox_tax_office': line.partner_tax_office,
                'email': line.partner_email,
                'system': line.company_id.system,
                'company_id': line.company_id.id,
            })

        if line.user_name:
            user = self.env['res.users'].search([('partner_id.name', '=', line.user_name)], limit=1)
            user_values = {}
            if line.user_email:
                user_values.update({'email': line.user_email})
            if line.user_mobile:
                user_values.update({'mobile': line.user_mobile})
            if not user:
                user = self.env['res.users'].create({'name': line.user_name})
            if user_values:
                user.partner_id.write(user_values)
            partner.user_id = user.id
        
        if line.bank_iban:
            bank = partner.bank_ids.filtered(lambda b: b.acc_number == line.bank_iban)
            if bank:
                bank.api_merchant = line.bank_merchant
            else:
                partner.bank_ids = [(0, 0, {'acc_number': line.bank_iban, 'api_merchant': line.bank_merchant})]

        return {
            'parent_id': partner.id,
            'amount': line.amount,
            'date': line.date,
            'due_date': line.due_date,
            'ref': line.ref,
            'tag': line.tag,
            'description': line.description,
            'system': line.company_id.system,
            'currency_id': line.currency_id.id,
            'company_id': line.company_id.id,
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
                    if not 'Partner Name' in cols:
                        raise UserError(_('Please create a "Partner Name" column'))
                    if not 'Partner VAT' in cols:
                        raise UserError(_('Please create a "Partner VAT" column'))
                    if not 'Partner Email' in cols:
                        raise UserError(_('Please create a "Partner Email" column'))
                    elif not 'Amount' in cols:
                        raise UserError(_('Please create a "Amount" column'))
                else:
                    val = dict(zip(cols, row))
                    if isinstance(val['Partner VAT'], float):
                        val['Partner VAT'] = '%.0f' % val['Partner VAT']
                    vals = self._get_row(val)
                    if 'Currency' in val:
                        currency = self.env['res.currency'].search([('name', '=', val['Currency'])], limit=1)
                        if currency:
                            vals['currency_id'] = currency.id
                    if 'Company' in val:
                        company = self.env['res.company'].search([('name', '=', val['Company'])], limit=1)
                        if company:
                            vals['company_id'] = company.id
                    values.append(vals)
            self.line_ids = [(5, 0, 0)] + [(0, 0, value) for value in values]

        else:
            self.line_ids = [(5, 0, 0)]

    def confirm(self):
        items = self.env['payment.item']
        for line in self.line_ids:
            row = self._prepare_row(line)
            items.create(row)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class PaymentItemImportLine(models.TransientModel):
    _name = 'payment.item.import.line'
    _description = 'Payment Item Import Line'

    wizard_id = fields.Many2one('payment.item.import')
    partner_id = fields.Many2one('res.partner', readonly=True)
    partner_name = fields.Char('Partner Name', readonly=True)
    partner_vat = fields.Char('Partner VAT', readonly=True)
    partner_email = fields.Char('Partner Email', readonly=True)
    partner_street = fields.Char('Partner Street', readonly=True)
    partner_tax_office = fields.Char('Partner Tax Office', readonly=True)
    amount = fields.Monetary('Amount', readonly=True)
    date = fields.Date('Date', readonly=True)
    due_date = fields.Date('Due Date', readonly=True)
    ref = fields.Char('Reference', readonly=True)
    tag = fields.Char('Tag', readonly=True)
    bank_iban = fields.Char('IBAN', readonly=True)
    bank_merchant = fields.Char('Merchant', readonly=True)
    user_id = fields.Many2one('res.users', 'Sales Representative', readonly=True)
    user_name = fields.Char('Sales Representative Name', readonly=True)
    user_email = fields.Char('Sales Representative Email', readonly=True)
    user_mobile = fields.Char('Sales Representative Mobile', readonly=True)
    description = fields.Char('Description', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True, required=True, default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', readonly=True, required=True, default=lambda self: self.env.company)
