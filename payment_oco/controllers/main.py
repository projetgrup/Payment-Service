# -*- coding: utf-8 -*-
from odoo import _
from odoo.http import route, request
from odoo.addons.portal.controllers import portal
from odoo.addons.payment_jetcheckout_system.controllers.main import PayloxSystemController as Controller


class CustomerPortal(portal.CustomerPortal):
    @route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kwargs):
        system = kwargs.get('system', request.env.company.system)
        if system == 'oco':
            return request.redirect('/my/payment')
        return super().home(**kwargs)


#class PayloxSystemOcoController(Controller):
#    
#    def _get_tx_values(self, **kwargs):
#        values = super()._get_tx_values(**kwargs)
#        if request.env.company.system == 'oco':
#            values.update({'jetcheckout_preauth': True})
#        return values
