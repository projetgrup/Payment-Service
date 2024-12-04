# -*- coding: utf-8 -*-
from odoo import _lt
from marshmallow import fields
from odoo.addons.datamodel.core import Datamodel
from odoo.addons.datamodel.fields import NestedModel


class OcoPaymentPartner(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.partner"

    name = fields.String(required=True, allow_none=False, metadata={"title": _lt("Partner Name"), "description": _lt("Partner name"), "example": "John Doe"})
    vat = fields.String(required=True, allow_none=False, metadata={"title": _lt("Partner VAT"), "description": _lt("Partner VAT number"), "example": "12345678910"})
    email = fields.String(required=True, allow_none=False, metadata={"title": _lt("Email Address"), "description": _lt("Email address"), "example": "test@example.com"})
    phone = fields.String(required=True, allow_none=False, metadata={"title": _lt("Phone Number"), "description": _lt("Phone number"), "example": "+905321234567"})
    ip_address = fields.String(required=True, allow_none=False, metadata={"title": _lt("IP Address"), "description": _lt("IP Address"), "example": "34.06.50.01"})
    country = fields.String(required=False, allow_none=False, metadata={"title": _lt("Country Code"), "description": _lt("Country code"), "example": "TR"})
    state = fields.String(required=False, allow_none=False, metadata={"title": _lt("State Code"), "description": _lt("State code"), "example": "34"})
    city = fields.String(required=False, allow_none=True, metadata={"title": _lt("City/Town Name"), "description": _lt("City/Town name"), "example": "Beyoğlu"})
    address = fields.String(required=False, allow_none=False, metadata={"title": _lt("Partner Address"), "description": _lt("Partner address"), "example": "Example Street, No: 1"})
    zip = fields.String(required=False, allow_none=True, metadata={"title": _lt("ZIP Code"), "description": _lt("ZIP Code"), "example": "34100"})
    contact = fields.String(required=False, allow_none=False, metadata={"title": _lt("Contact Name"), "description": _lt("Contact name"), "example": "Jane Doe"})


class OcoPaymentCompany(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.company"

    vat = fields.String(required=True, allow_none=False, metadata={"title": _lt("Company VAT"), "description": _lt("Company VAT number"), "example": "12345678910"})


class OcoPaymentOrder(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.order"

    name = fields.String(required=True, allow_none=False, metadata={"title": _lt("Order Name"), "description": _lt("Order name"), "example": "S123564"})
    products = fields.List(NestedModel("payment.product"), required=False, metadata={"title": _lt("Products List"), "description": _lt("List of related products")})
    amount = fields.Float(required=False, allow_none=False, metadata={"title": _lt("Amount"), "description": _lt("Amount to pay. If it is not sent, sum of total prices of products will be used."), "example": 145.3})


class OcoPaymentUrl(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.url"

    redirect = fields.String(required=True, allow_none=False, metadata={"title": _lt("Redirect URL"), "description": _lt("URL to redirect after payment operation"), "example": "https://example.com/redirect"})


class OrderCheckoutPaymentCreateRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.create.request"
    _inherit = "payment.credential.hash"

    id = fields.Integer(required=True, allow_none=False, metadata={"title": "ID", "description": _lt("Any unique number related to your specified record in your database for tracking the payment flow"), "example": 12})
    expiration = fields.DateTime(allow_none=False, metadata={"title": _lt("Expiration Date"), "description": _lt("Datetime in ISO format to get transaction expired"), "example": "2023-01-01T00:00:00"})
    campaign = fields.String(metadata={"title": _lt("Campaign Name"), "description": _lt("Name of campaign to be used in getting installment options"), "example": "Standard"})
    company = NestedModel("oco.payment.company", required=True, metadata={"title": _lt("Company information related to request"), "description": _lt("Company information")})
    partner = NestedModel("oco.payment.partner", required=True, metadata={"title": _lt("Partner information related to request"), "description": _lt("Partner information")})
    order = NestedModel("oco.payment.order", required=True, metadata={"title": _lt("Order information related to request"), "description": _lt("Order details")})
    url = NestedModel("oco.payment.url", required=True, metadata={"title": _lt("Return URLs by payment method"), "description": _lt("URL addresses")})
    preauth = fields.Boolean(metadata={"title": _lt("Preauth"), "description": _lt("Preauth"), "example": True, "default": True})
    html = fields.String(metadata={"title": _lt("Custom HTML"), "description": _lt("Custom code to be viewed bottom of the page"), "example": "<p>Copyright</p>"})

class OrderCheckoutPaymentCancelRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.cancel.request"
    _inherit = "payment.credential.hash"

    id = fields.UUID(required=True, allow_none=False, metadata={"title": "ID", "description": _lt("Any unique number related to your specified record in your database for tracking the payment flow"), "example": "9ee3fd53-42f9-4f16-b454-77e6b714c2e9"})


class OrderCheckoutPaymentRefundRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.refund.request"
    _inherit = "payment.credential.hash"

    id = fields.UUID(required=True, allow_none=False, metadata={"title": "ID", "description": _lt("Any unique number related to your specified record in your database for tracking the payment flow"), "example": "9ee3fd53-42f9-4f16-b454-77e6b714c2e9"})
    amount = fields.Float(required=True, allow_none=False, metadata={"title": _lt("Amount"), "description": _lt("Amount to be refunded"), "example": 50.20})


class OrderCheckoutPaymentQueryRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.query.request"
    _inherit = "payment.credential.hash"

    id = fields.UUID(required=True, allow_none=False, metadata={"title": "ID", "description": _lt("Any unique number related to your specified record in your database for tracking the payment flow"), "example": "9ee3fd53-42f9-4f16-b454-77e6b714c2e9"})


class OrderCheckoutPaymentPostauthRequest(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.postauth.request"
    _inherit = "payment.credential.hash"

    id = fields.UUID(required=True, allow_none=False, metadata={"title": "ID", "description": _lt("Any unique number related to your specified record in your database for tracking the payment flow"), "example": "9ee3fd53-42f9-4f16-b454-77e6b714c2e9"})


class OrderCheckoutPaymentCreateResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.create.response"
    _inherit = "payment.output"

    id = fields.UUID(required=False, allow_none=False, metadata={"title": _lt("ID"), "description": _lt("Payment ID"), "example": "9ee3fd53-42f9-4f16-b454-77e6b714c2e9"})
    url = fields.String(required=False, allow_none=False, metadata={"title": _lt("URL"), "description": _lt("Payment URL which redirects to payment page"), "example": "https://example.com/payment?=LkuxD5WGo/81sqn6ZS6/a0qjdSX1cQWl8tHc5NseGto="})
    #url = fields.String(required=False, allow_none=False, metadata={"title": _lt("URL"), "description": _lt("Payment URL which redirects to payment page"), "example": "https://example.com/payment?=9ee3fd53-42f9-4f16-b454-77e6b714c2e9"})

class OrderCheckoutPaymentCancelResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.cancel.response"
    _inherit = "payment.output"


class OrderCheckoutPaymentRefundResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.refund.response"
    _inherit = "payment.output"


class OrderCheckoutPaymentPostauthResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.postauth.response"
    _inherit = "payment.output"


class OrderCheckoutPaymentQueryResponse(Datamodel):
    class Meta:
        ordered = True

    _name = "oco.payment.query.response"
    _inherit = "payment.output"

    date = fields.DateTime(required=False, allow_none=False, metadata={"title": _lt("Date"), "description": _lt("Payment Date"), "example": "2025-01-01"})
    vpos_id = fields.Integer(required=False, allow_none=False, metadata={"title": _lt("Virtual PoS ID"), "description": _lt("Virtual PoS ID"), "example": 1})
    vpos_name = fields.String(required=False, allow_none=False, metadata={"title": _lt("Virtual PoS Name"), "description": _lt("Virtual PoS Name"), "example": "ZiraatBank"})
    vpos_ref = fields.String(required=False, allow_none=False, metadata={"title": _lt("Virtual PoS Reference"), "description": _lt("Virtual PoS Reference"), "example": "9ee3fd53-42f9-4f16-b454-77e6b714c2e9"})
    vpos_code = fields.String(required=False, allow_none=False, metadata={"title": _lt("Virtual PoS Code"), "description": _lt("Virtual PoS Code"), "example": "VPOS01"})
    successful = fields.Boolean(required=False, allow_none=False, metadata={"title": _lt("Successful"), "description": _lt("Successful"), "example": True})
    completed = fields.Boolean(required=False, allow_none=False, metadata={"title": _lt("Completed"), "description": _lt("Completed"), "example": True})
    cancelled = fields.Boolean(required=False, allow_none=False, metadata={"title": _lt("Cancelled"), "description": _lt("Cancelled"), "example": False})
    preauth = fields.Boolean(required=False, allow_none=False, metadata={"title": _lt("Pre-Authorization"), "description": _lt("Pre-Authorization"), "example": True})
    postauth = fields.Boolean(required=False, allow_none=False, metadata={"title": _lt("Post-Authorization"), "description": _lt("Post-Authorization"), "example": True})
    threed = fields.Boolean(required=False, allow_none=False, metadata={"title": _lt("3D Payment"), "description": _lt("3D Payment"), "example": True})
    amount = fields.Float(required=False, allow_none=False, metadata={"title": _lt("Amount"), "description": _lt("Payment Amount"), "example": 25750.00})
    cost_amount = fields.Float(required=False, allow_none=False, metadata={"title": _lt("Cost Amount"), "description": _lt("Cost Amount"), "example": 257.50})
    cost_rate = fields.Float(required=False, allow_none=False, metadata={"title": _lt("Cost Rate"), "description": _lt("Cost Rate"), "example": 1})
    customer_amount = fields.Float(required=False, allow_none=False, metadata={"title": _lt("Customer Amount"), "description": _lt("Customer Amount"), "example": 257.50})
    customer_rate = fields.Float(required=False, allow_none=False, metadata={"title": _lt("Customer Rate"), "description": _lt("Customer Rate"), "example": 1})
    auth_code = fields.String(required=False, allow_none=False, metadata={"title": _lt("Authorization Code"), "description": _lt("Authorization Code"), "example": "C001"})
    card_family = fields.String(required=False, allow_none=False, metadata={"title": _lt("Credit Card Family"), "description": _lt("Credit Card Family"), "example": "Visa"})
    card_program = fields.String(required=False, allow_none=False, metadata={"title": _lt("Credit Card Program"), "description": _lt("Credit Card Program"), "example": "Bankkart"})
    bin_code = fields.String(required=False, allow_none=False, metadata={"title": _lt("Credit Card BIN Code"), "description": _lt("Credit Card BIN Code"), "example": "123456"})
    service_ref_id = fields.String(required=False, allow_none=False, metadata={"title": _lt("Service Reference ID"), "description": _lt("Service Reference ID"), "example": "123456"})
    service_code = fields.String(required=False, allow_none=False, metadata={"title": _lt("Service Code"), "description": _lt("Service Code"), "example": "01"})
    service_message = fields.String(required=False, allow_none=False, metadata={"title": _lt("Service Message"), "description": _lt("Service Message"), "example": "Success"})
