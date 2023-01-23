# -*- coding: utf-8 -*-
import uuid
from odoo import models, fields, api


class PosBank(models.Model):
    _name = 'pos.bank'
    _description = 'Point of Sale - Bank'
    _order = 'sequence'

    config_id = fields.Many2one('pos.config')
    sequence = fields.Integer(default=10)
    logo = fields.Image()
    name = fields.Char(required=True)
    iban = fields.Char(string='IBAN')
    account = fields.Char(string='Account Number')
    branch = fields.Char()
    token = fields.Char(default=lambda self: str(uuid.uuid4()), readonly=True)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    cash_payment_limit_ok = fields.Boolean(string='Limit Cash Payment Amount')
    cash_payment_limit_amount = fields.Monetary(string='Cash Payment Amount Limit')
    bank_ids = fields.One2many('pos.bank', 'config_id', string='Banks')
    bank_ok = fields.Boolean(string='Show Bank Accounts')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, copy=False)

    @api.model
    def _order_fields(self, ui_order):
        res = super()._order_fields(ui_order)
        delivery = ui_order['partner_address']['delivery']
        res['partner_shipping_id'] = delivery and delivery['id'] or False
        return res

    def _create_order_picking(self):
        self.ensure_one()
        if self._should_create_picking_real_time() and self.partner_shipping_id:
            self = self.with_context(partner_shipping_id=self.partner_shipping_id)
        return super(PosOrder, self)._create_order_picking()


class StockPicking(models.Model):
    _inherit='stock.picking'

    def _prepare_picking_vals(self, partner, picking_type, location_id, location_dest_id):
        res = super(StockPicking, self)._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
        partner_shipping_id = self.env.context.get('partner_shipping_id')
        if partner_shipping_id:
            res['partner_id'] = partner_shipping_id.id
        return res
