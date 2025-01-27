# -*- coding: utf-8 -*-
from odoo import fields, models, api, SUPERUSER_ID, _


class PaymentPayloxApiPos(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.api.pos'
    _description = 'Paylox API Pos'
    _remote_name = 'jet.virtual.pos'

    acquirer_id = fields.Many2one('payment.acquirer')
    applications = fields.Many2many('payment.acquirer.jetcheckout.api.application', 'payment_jetcheckout_api_application_pos_rel', 'pos_id', 'application_id', string='Applications', ondelete='cascade')
    pos_price = fields.One2many('payment.acquirer.jetcheckout.api.campaign', 'virtual_pos_id', 'Campaigns')
    parent_id = fields.Many2one('payment.acquirer.jetcheckout.api.poses')
    res_id = fields.Integer(readonly=True)
    name = fields.Char(required=True)
    payment_org_id = fields.Many2one('payment.acquirer.jetcheckout.api.provider', string='Provider', readonly=True, required=True)
    is_active = fields.Boolean('Active', default=True)
    is_client_active = fields.Boolean(related='payment_org_id.client_active')
    is_merchant_active = fields.Boolean(related='payment_org_id.merchant_active')
    is_apikey_active = fields.Boolean(related='payment_org_id.apikey_active')
    is_terminal_active = fields.Boolean(related='payment_org_id.terminal_active')
    is_username_active = fields.Boolean(related='payment_org_id.username_active')
    is_password_active = fields.Boolean(related='payment_org_id.password_active')
    is_refid_active = fields.Boolean(related='payment_org_id.refid_active')
    is_rfnd_username_active = fields.Boolean(related='payment_org_id.rfnd_username_active')
    is_rfnd_password_active = fields.Boolean(related='payment_org_id.rfnd_password_active')    
    client_id = fields.Char('Client ID')
    merchant_id = fields.Char('Merchant ID')
    terminal_id = fields.Char('Terminal ID')
    api_key = fields.Char('API Key')
    secret_key = fields.Char('Secret Key', required=True)
    username = fields.Char('Username')
    password = fields.Char('Password')
    rfnd_username = fields.Char('Refund Username')
    rfnd_password = fields.Char('Refund Password')
    ref_id = fields.Char('Ref ID')
    priority = fields.Integer('Priority', required=True)
    usage_3d = fields.Selection([('Not Usable','Not Usable'),('Choosable','Choosable'),('Mandatory','Mandatory')], string='3D Usage')
    mode = fields.Selection([('P','Production'),('T','Test')], string='Mode', required=True, default='T')
    is_physical = fields.Boolean('Physical POS', readonly=True)
    rates_importable = fields.Boolean('Rates Importable', readonly=True)
    import_rates = fields.Boolean('Import Commission Rates')
    calc_cust_rates = fields.Boolean('Calculate Customer Rates')
    excluded_card_families = fields.Many2many('payment.acquirer.jetcheckout.api.family', 'payment_jetcheckout_api_excluded_pos_rel', 'pos_id', 'family_id', string='Excluded Card Families', domain='[("acquirer_id", "=", acquirer_id)]')
    notes = fields.Text('Notes', readonly=True)

    customer_ip = fields.Char()
    customer_email = fields.Char()
    customer_name = fields.Char()
    customer_surname = fields.Char()
    customer_address = fields.Char()
    customer_phone = fields.Char()
    customer_id = fields.Char()
    customer_identity = fields.Char()
    customer_city = fields.Char()
    customer_country = fields.Char()
    customer_postal_code = fields.Char()
    customer_company = fields.Char()
    basket_item_id = fields.Char()
    basket_item_name = fields.Char()
    basket_item_desc = fields.Char()
    basket_item_categ = fields.Char()
    billing_address_contact = fields.Char()
    billing_address = fields.Char()
    billing_address_city = fields.Char()
    billing_address_country = fields.Char()
    shipping_address_contact = fields.Char()
    shipping_address = fields.Char()
    shipping_address_city = fields.Char()
    shipping_address_country = fields.Char()

    @api.onchange('payment_org_id')
    def onchange_provider(self):
        self.customer_ip = self.payment_org_id.customer_ip
        self.customer_email = self.payment_org_id.customer_email
        self.customer_name = self.payment_org_id.customer_name
        self.customer_surname = self.payment_org_id.customer_surname
        self.customer_address = self.payment_org_id.customer_address
        self.customer_phone = self.payment_org_id.customer_phone
        self.customer_id = self.payment_org_id.customer_id
        self.customer_identity = self.payment_org_id.customer_identity
        self.customer_city = self.payment_org_id.customer_city
        self.customer_country = self.payment_org_id.customer_country
        self.customer_postal_code = self.payment_org_id.customer_postal_code
        self.customer_company = self.payment_org_id.customer_company
        self.billing_address_contact = self.payment_org_id.billing_address_contact
        self.billing_address = self.payment_org_id.billing_address
        self.billing_address_city = self.payment_org_id.billing_address_city
        self.billing_address_country = self.payment_org_id.billing_address_country
        self.shipping_address_contact = self.payment_org_id.shipping_address_contact
        self.shipping_address = self.payment_org_id.shipping_address
        self.shipping_address_city = self.payment_org_id.shipping_address_city
        self.shipping_address_country = self.payment_org_id.shipping_address_country
        self.basket_item_id = self.payment_org_id.basket_item_id
        self.basket_item_name = self.payment_org_id.basket_item_name
        self.basket_item_desc = self.payment_org_id.basket_item_desc
        self.basket_item_categ = self.payment_org_id.basket_item_categ

    @api.onchange('calc_cust_rates')
    def onchange_calc_cust_rates(self):
        if (isinstance(self._origin.id, int)):
            self.browse(self._origin.id).write({'calc_cust_rates': True})

    def import_cost_rates(self):
        self.acquirer_id._rpc('jet.virtual.pos', 'import_cost_rates', self.res_id)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if 'res_id' not in vals:
            id = res.acquirer_id._rpc(res, 'create', vals)
            res.write({'res_id': id})
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'res_id' not in vals:
            for pos in self:
                pos.acquirer_id._rpc(pos, 'write', pos.res_id, vals)
                pos.acquirer_id._paylox_api_sync_campaign()
        return res

    def unlink(self):
        if self.env.uid == SUPERUSER_ID:
            return super().unlink()

        if not self.env.context.get('no_sync'):
            for pos in self:
                pos.acquirer_id._rpc(pos._remote_name, 'unlink', pos.res_id)
        return super().unlink()


class PaymentPayloxApiCurrency(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.api.currency'
    _description = 'Paylox API Currencies'

    acquirer_id = fields.Many2one('payment.acquirer')
    res_id = fields.Integer(readonly=True)
    name = fields.Char(readonly=True)


class PaymentPayloxApiProvider(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.api.provider'
    _description = 'Paylox API Providers'
    _remote_name = 'jet.payment.org'

    acquirer_id = fields.Many2one('payment.acquirer')
    res_id = fields.Integer(readonly=True)
    code = fields.Char(readonly=True)
    name = fields.Char(readonly=True)

    merchant_active = fields.Boolean()
    client_active = fields.Boolean()
    apikey_active = fields.Boolean()
    terminal_active = fields.Boolean()
    username_active = fields.Boolean()
    password_active = fields.Boolean()
    refid_active = fields.Boolean()
    rfnd_username_active = fields.Boolean()
    rfnd_password_active = fields.Boolean()

    customer_ip = fields.Char()
    customer_email = fields.Char()
    customer_name = fields.Char()
    customer_surname = fields.Char()
    customer_address = fields.Char()
    customer_phone = fields.Char()
    customer_id = fields.Char()
    customer_identity = fields.Char()
    customer_city = fields.Char()
    customer_country = fields.Char()
    customer_postal_code = fields.Char()
    customer_company = fields.Char()
    basket_item_id = fields.Char()
    basket_item_name = fields.Char()
    basket_item_desc = fields.Char()
    basket_item_categ = fields.Char()
    billing_address_contact = fields.Char()
    billing_address = fields.Char()
    billing_address_city = fields.Char()
    billing_address_country = fields.Char()
    shipping_address_contact = fields.Char()
    shipping_address = fields.Char()
    shipping_address_city = fields.Char()
    shipping_address_country = fields.Char()


class PaymentPayloxApiPoses(models.TransientModel):
    _name = 'payment.acquirer.jetcheckout.api.poses'
    _description = 'Paylox Poses'

    acquirer_id = fields.Many2one('payment.acquirer', readonly=True)
    pos_ids = fields.One2many('payment.acquirer.jetcheckout.api.pos', 'parent_id', 'Poses')
    application_id = fields.Char(readonly=True)

    def write(self, vals):
        data = self.acquirer_id._paylox_api_read()
        self.acquirer_id._paylox_api_upload(vals, data, self)
        self.acquirer_id._paylox_api_sync_campaign()
        return super().write(vals)
