# -*- coding: utf-8 -*-
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(self):
        mods = super(IrHttp, self)._get_translation_frontend_modules_name()
        return mods + ['payment_system_product']

    def binary_content(self, xmlid=None, model='ir.attachment', id=None, field='datas',
        unique=False, filename=None, filename_field='name', download=False,
        mimetype=None, default_mimetype='application/octet-stream',
        access_token=None
    ):
        obj = None
        if xmlid:
            obj = self._xmlid_to_obj(self.env, xmlid)
        elif id and model in self.env:
            obj = self.env[model].browse(int(id))
        if obj and 'payment_page_ok' in obj._fields and field in obj._fields and not obj._fields[field].groups and obj.sudo().payment_page_ok:
            self = self.sudo()
        return super(IrHttp, self).binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype=default_mimetype, access_token=access_token
        )
