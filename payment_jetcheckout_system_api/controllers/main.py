# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.addons.payment_jetcheckout_system.controllers.main import PayloxSystemController as Controller


class PayloxSystemApiController(Controller):

    def _get_template(self, path, values):
        if 'tx' in values and values['tx']['jetcheckout_api_ok']:
            template = request.env['payment.view'].sudo().search([
                ('page_id.path', '=', path),
                '|',
                ('company_id', '=', values['company']['id'] or 0),
                ('company_id', '=', values['company']['parent_id']['id'] or 0),
            ], order='id desc', limit=1)
            if template:
                values.update({
                    'template': {
                        'id': template.uid,
                        'js': bool(template.arch_js),
                        'css': bool(template.arch_css),
                    }
                })
                return template.view_id.id
            if path == '/payment/card':
                return 'payment_jetcheckout_api.page_card'
            return 'payment_jetcheckout_api.payment_page'
        return super()._get_template(path, values)
