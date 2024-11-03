# -*- coding: utf-8 -*-
import re
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.payment_jetcheckout.controllers.main import PayloxController as Controller


class PayloxSystemOtpController(Controller):

    @http.route('/otp', type='http', auth='public', methods=['GET'], sitemap=False, website=True)
    def page_system_otp(self, **kwargs):
        company = request.env.company
        companies = request.env['website'].sudo().search([('domain', '=', request.website.domain)]).mapped('company_id')
        system = company.system
        values = {
            'company': company,
            'companies': companies,
            'website': request.website,
            'footer': request.website.payment_footer,
            'system': system,
            'tags': [],
        }
        return request.render('payment_jetcheckout_system_otp.page_otp', values)

    @http.route(['/otp/prepare'], type='json', auth='public', sitemap=False, website=True)
    def page_system_otp_prepare(self, **kwargs):
        if re.search(r'\W', kwargs['login']):
            return {
                'error': _('Only alphanumeric characters are allowed')
            }

        company = request.env.company
        login = kwargs['login']
        query = f"""
SELECT id
FROM res_partner
WHERE active IS TRUE
AND company_id = {company.id}
AND parent_id IS NULL
AND (
    email = '{login}'
    OR ref = '{login}'
    OR RIGHT(REPLACE(phone, ' ', ''), 10) = '{login}'
    OR RIGHT(REPLACE(mobile, ' ', ''), 10) = '{login}'
)
LIMIT 1
"""
        request.env.cr.execute(query)
        result = request.env.cr.fetchone()

        id = 0
        email = 'a***@a***.com'
        phone = '+90 5** *** 1234'
        vat = '90*******00'
        ref = '12*******34'
        if result:
            partner = request.env['res.partner'].sudo().browse(result[0])
            id = request.env['res.partner.otp'].sudo().create({
                'partner_id': partner.id,
                'company_id': partner.company_id.id,
                'lang': partner.lang,
            }).id

            email = partner.email
            if '@' in email and '.' in email:
                name, domain = email.split('@', 1)
                address, suffix = domain.split('.', 1)
                email = '%s***@%s***.%s' % (name[0], address[0], suffix)
            else:
                email = '-'

            phone = partner.mobile or partner.phone
            if phone:
                phone = '+90 5** *** %s' % phone[-4:]
            else:
                phone = '-'

            if partner.child_ids:
                child = partner.child_ids.filtered(lambda x: x.vat and login in x.vat)
                if child:
                    vat = child.vat
                    vat = '%s******%s' % (vat[:2], vat[-2:]) if vat and len(vat) > 5 else '-'
                else:
                    vat = partner.child_ids[0].vat
                    vat = '%s******%s' % (vat[:2], vat[-2:]) if vat and len(vat) > 5 else '-'

                child = partner.child_ids.filtered(lambda x: x.ref and login == x.ref)
                if child:
                    ref = child.ref
                    ref = '%s******%s' % (ref[:2], ref[-2:]) if ref and len(ref) > 5 else '-'
                else:
                    ref = partner.child_ids[0].ref
                    ref = '%s******%s' % (ref[:2], ref[-2:]) if ref and len(ref) > 5 else '-'
            else:
                vat = '-'
                ref = '-'

        return {
            'id': id,
            'email': email,
            'phone': phone,
            'vat': vat,
            'ref': ref,
        }


    @http.route(['/otp/company'], type='json', auth='public', website=True, csrf=False)
    def page_system_otp_company(self, cid):
        if cid == request.env.company.id:
            return False

        website = request.env['website'].sudo().search([
            ('domain', '=', request.website.domain),
            ('company_id', '=', cid)
        ], limit=1)
        if not website:
            return False

        website._force()
        return True

    @http.route(['/otp/validate'], type='json', auth='public', sitemap=False, website=True)
    def page_system_otp_validate(self, **kwargs):
        company = request.env.company
        otp = request.env['res.partner.otp'].sudo().search([
            ('company_id', '=', company.id),
            ('partner_id', '!=', False),
            ('id', '=', kwargs['id']),
            ('code', '=', kwargs['code']),
            ('date', '>', fields.Datetime.now())
        ], limit=1)

        if otp:
            return {
                'url': '%s/%s' % (company.otp_redirect_url or '/my/payment', otp.partner_id._get_token())
            }
        else:
            return {
                'error': _('Authentication code is not correct. Please check and retype.')
            }
