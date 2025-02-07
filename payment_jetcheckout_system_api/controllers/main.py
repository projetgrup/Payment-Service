# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.addons.payment_jetcheckout_api.controllers.main import PayloxApiController as Controller


class PayloxSystemApiController(Controller):

    def _get_template(self, path, values):
        template = request.env['payment.view'].sudo().search([
            ('page_id.path', '=', path),
            ('company_id', '=', values['company']['id']),
        ], limit=1)
        if template:
            values.update({
                'template': {
                    'id': template.uid,
                    'js': bool(template.arch_js),
                    'css': bool(template.arch_css),
                }
            })
            return template.view_id.id
        return super()._get_template(path, values)
