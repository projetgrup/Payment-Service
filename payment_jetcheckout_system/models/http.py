# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.http import request
from odoo.tools import frozendict


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super(Http, cls)._get_translation_frontend_modules_name()
        return mods + ['payment_jetcheckout_system']

    @staticmethod
    def _get_current_system():
        system = request.env['res.company']._fields['system'].selection
        if system:
            cids = request.httprequest.cookies.get('cids')
            if cids:
                cids = cids.split(',') if ',' in cids else [cids]
            else:
                query = f"""SELECT company_id FROM res_users WHERE id={request.session.uid}"""
                request.env.cr.execute(query)
                cids = request.cr.fetchone()

            query = f"""SELECT system, subsystem FROM res_company WHERE id={cids[0]}"""
            request.env.cr.execute(query)

            context = dict(request.context)
            context['system'], context['subsystem'] = request.cr.fetchone()
            request.context = frozendict(context)

    def webclient_rendering_context(self):
        return {
            'session_info': self.session_info(),
            'menu_data': request.env['ir.ui.menu'].load_menus(request.session.debug),
        }

    def session_info(self):
        self._get_current_system()
        res = super(Http, self).session_info()
        if res['user_context'].get('system'):
            res['home_action_id'] = self.env.ref('payment_jetcheckout_system.action_dashboard').id
        return res
