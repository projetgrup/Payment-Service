# -*- coding: utf-8 -*-

import uuid
import json
import base64
from datetime import datetime
from odoo import models, fields, _
from odoo.tools.misc import formatLang
from odoo.tools.translate import xml_translate


class PaymentAgreement(models.Model):
    _name = 'payment.agreement'
    _description = 'Payment System Agreement'
    _order = 'sequence, id'

    def _compute_body(self):
        for agreement in self:
            tr = self._fields['arch'].get_trans_func(agreement)
            agreement.body = tr(agreement.id, agreement.arch)

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    name = fields.Char(translate=True)
    text = fields.Char(translate=True)
    body = fields.Html(translate=True, sanitize=False, compute='_compute_body')
    arch = fields.Text(translate=xml_translate)
    date_start = fields.Date('Start Date')
    date_end = fields.Date('End Date')
    version = fields.Char()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    page_ids = fields.Many2many('payment.page', 'payment_agreement_page_rel', 'agreement_id', 'page_id', string='Pages')
    product_ids = fields.Many2many('product.template', 'payment_agreement_product_rel', 'agreement_id', 'product_id', string='Products')
    type_ids = fields.Many2many('ir.model.fields.selection', 'payment_agreement_type_rel', 'agreement_id', 'type_id', string='Types', domain=[('field_id.name', '=', 'jetcheckout_payment_type')])

    def open_translations(self):
        return self.env['ir.translation'].translate_fields(self._name, self.id, 'arch')

    def render(self, **values):
        partner = values.get('partner', None)
        partner_name = partner and partner.name or ''
        partner_vat = partner and partner.vat or ''
        partner_tax_office = partner and partner.paylox_tax_office or ''
        partner_company_name = partner and partner.commercial_partner_id.name or ''
        partner_address = partner and partner._display_address() or ''
        partner_phone = partner and partner.phone or ''
        partner_mobile = partner and partner.mobile or ''
        partner_email = partner and partner.email or ''
        partner_website = partner and partner.website or ''
        payment_currency = values.get('currency', self.company_id.currency_id)
        payment_amount = formatLang(self.env, values.get('amount', 0), monetary=True, currency_obj=payment_currency)
        agreement = self.body \
            .replace('{{ partner_name }}', partner_name) \
            .replace('{{ partner_vat }}', partner_vat) \
            .replace('{{ partner_tax_office }}', partner_tax_office) \
            .replace('{{ partner_company_name }}', partner_company_name) \
            .replace('{{ partner_address }}', partner_address) \
            .replace('{{ partner_phone }}', partner_phone) \
            .replace('{{ partner_mobile }}', partner_mobile) \
            .replace('{{ partner_email }}', partner_email) \
            .replace('{{ partner_website }}', partner_website) \
            .replace('{{ payment_amount }}', payment_amount)
        return self.env['mail.render.mixin'].with_context(datetime=datetime, json=json, **values)._render_template(agreement, self._name, self.ids, engine='qweb')[self.id]
        return agreement

    def render_pdf(self, **values):
        body = self.render(**values)
        icp = self.env['ir.config_parameter'].sudo()
        base_url = icp.get_param('report.url') or icp.get_param('web.base.url')
        layout = self.env.ref('payment_jetcheckout.report_layout')
        html = layout._render({'body': body, 'base_url': base_url})
        pdf = self.env['ir.actions.report']._run_wkhtmltopdf(
            [html],
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10,
            }
        )
        return base64.b64encode(pdf)

    def action_toggle_active(self):
        self.active = not self.active


class PaymentTransactionAgreement(models.Model):
    _name = 'payment.transaction.agreement'
    _description = 'Payment System Transaction Agreement'
    _order = 'id desc'

    def _compute_name(self):
        for tx in self:
            tx.name = tx.agreement_id.name

    path = fields.Char(readonly=True)
    pdf = fields.Binary(readonly=True)
    active = fields.Boolean(readonly=True)
    name = fields.Char(compute='_compute_name')
    body = fields.Html(sanitize=False, readonly=True)
    uuid = fields.Char('UUID', readonly=True, copy=False, default=lambda self: str(uuid.uuid4()))
    ip_address = fields.Char('IP Address', readonly=True)
    page_id = fields.Many2one('payment.page', readonly=True)
    agreement_id = fields.Many2one('payment.agreement', readonly=True)
    transaction_id = fields.Many2one('payment.transaction', readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)

    def render(self):
        tx = self.transaction_id
        return self.agreement_id.with_context(lang=tx.partner_lang).render(
            amount=tx.amount,
            partner=tx.partner_id,
            currency=tx.currency_id,
            transaction=tx,
        )

    def action_pdf(self):
        if not self.pdf:
            icp = self.env['ir.config_parameter'].sudo()
            base_url = icp.get_param('report.url') or icp.get_param('web.base.url')
            layout = self.env.ref('payment_jetcheckout.report_layout')
            html = layout._render({'body': self.body, 'base_url': base_url})
            pdf = self.env['ir.actions.report']._run_wkhtmltopdf(
                [html],
                specific_paperformat_args={
                    'data-report-margin-top': 10,
                    'data-report-header-spacing': 10,
                }
            )
            self.sudo().write({'pdf': base64.b64encode(pdf)})
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '/web/content/%s/%s/pdf?mimetype=application%%2Fpdf&download=True' % (self._name, self.id)
        }

    def action_transaction(self):
        self.ensure_one()
        action = self.env.ref('payment_jetcheckout_system.action_transaction').sudo().read()[0]
        action['res_id'] = self.transaction_id.id
        action['views'] = [[False, 'form']]
        return action
