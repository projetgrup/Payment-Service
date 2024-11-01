# -*- coding: utf-8 -*-
import json
import base64
import werkzeug
from urllib.parse import urlparse

from werkzeug.exceptions import NotFound

from .sse import dispatch
from odoo import _
from odoo.http import route, request, Response, Controller
from odoo.addons.portal.controllers import portal
from odoo.addons.payment_jetcheckout_system.controllers.main import PayloxSystemController as SystemController


class PaymentProductController(Controller):

    @route(['/longpolling/prices'], type='http', methods=['GET'], auth='public', cors='*')
    def payment_product_price(self, **kwargs):
        return Response(dispatch.poll(request.db, request.env.company.id, request.uid, request.context), headers={
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        })

class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        company = request.env.company
        Products = request.env['product.product'].sudo().with_context(system=company.system)
        if 'product_count' in counters:
            values['product_count'] = Products.search_count([
                ('system', '!=', False),
                ('payment_page_ok', '=', True),
                ('company_id', '=', company.id),
            ]) if Products.check_access_rights('read', raise_exception=False) else 0
        return values

    @route(['/my/orders', '/my/orders/page/<int:page>'], type='http', auth='public', website=True)
    def portal_my_orders(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        company = request.env.company
        user = request.env.user
        if not company.system:
            if not user.share:
                return super().portal_my_orders(page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, **kw)
            else:
                raise NotFound()
        
        values = self._prepare_portal_layout_values()
        return request.render('payment_system_product.portal_my_orders', values, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '-1'
        })

    @route('/my/products', type='http', auth='user', methods=['GET'], sitemap=False, website=True)
    def portal_my_products(self, page=1, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        company = request.env.company
        domain = [
            ('company_id', '=', company.id),
            ('system', '=', company.system),
            ('product_tmpl_id.payment_page_ok', '=', True),
        ]
        Products = request.env['product.product'].sudo().with_context(system=company.system)

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
        }

        if not sortby:
            sortby = 'date'

        order = searchbar_sortings[sortby]['order']
        count = Products.search_count(domain)
        pager = portal.pager(
            url='/my/products',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=count,
            page=page,
            step=self._items_per_page
        )
        products = Products.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['my_products_history'] = products.ids[:100]

        colors = {
            0: '#444444',
            1: '#F06050',
            2: '#F4A460',
            3: '#F7CD1F',
            4: '#6CC1ED',
            5: '#814968',
            6: '#EB7E7F',
            7: '#2C8397',
            8: '#475577',
            9: '#D6145F',
            10: '#30C381',
            11: '#9365B8',
        }

        values.update({
            'system': company.system,
            'subsystem': company.subsystem,
            'products': products,
            'pager': pager,
            'colors': colors,
            'sortby': sortby,
            'filterby': filterby,
            'default_url': '/my/products',
            'searchbar_filters': {},
            'searchbar_sortings': searchbar_sortings,
        })

        return request.render('payment_system_product.portal_my_products', values, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '-1'
        })

    @route('/my/products/save', type='json', auth='user', website=True)
    def portal_my_products_save(self, products):
        paid = request.env.user.partner_id.id
        pids = list(map(int, products.keys()))
        lines = request.env['payment.product.partner'].sudo().search([
            ('product_id', 'in', pids),
            ('partner_id', '=', paid),
        ])
        for line in lines:
            try:
                pid = str(line.product_id.id)
                if line.margin != products[pid]:
                    line.write({'margin': products[pid]})
                del products[pid]
            except:
                pass

        for pid, val in products.items():
            try:
                if val != 0.0:
                    lines.create({
                        'product_id': int(pid),
                        'partner_id': paid,
                        'margin': val,
                    })
            except:
                pass

        return {}


class PaymentSystemProductController(SystemController):

    def _get_tx_values(self, **kwargs):
        vals = super()._get_tx_values(**kwargs)
        products = kwargs.get('products', [])
        if products:
            vals.update({
                'paylox_product_ids': [(0, 0, {
                    'product_id': product['pid'],
                    'qty': product['qty'],
                }) for product in products]})
        return vals

    def _check_product_page(self, **kwargs):
        if not request.env.company.system_product:
            raise werkzeug.exceptions.NotFound()

    def _check_create_partner(self, **kwargs):
        if request.env.company.system_product:
            return False
        return super()._check_create_partner(**kwargs)

    def _redirect_product_page(self, website_id=None, company_id=None):
        website = False
        websites = request.env['website'].sudo()
        if website_id:
            website = websites.browse(website_id)
        elif company_id:
            website = websites.search([
                ('domain', '=', request.website.domain),
                ('company_id', '=', company_id)
            ], limit=1)

        if not website:
            raise werkzeug.exceptions.NotFound()

        website._force()
        path = request.httprequest.path
        query = request.httprequest.query_string
        if query:
            path += '?' + query.decode('utf-8')
        return werkzeug.utils.redirect(path)

    def _prepare_system(self,  company, system, partner, transaction, options={}):
        res = super()._prepare_system(company, system, partner, transaction, options=options)
        if company.system_product:
            products = request.env['product.template'].sudo().with_context(system=system, include_margin=True).search([
                ('system', '!=', False),
                ('company_id', '=', company.id),
                ('payment_page_ok', '=', True),
            ])
            categs = products.mapped('categ_id').sorted(lambda c: (c.sequence, c.id))
            if res['partner']['payment_product_categ_ids']:
                categs = categs.filtered(lambda c: c.id in res['partner']['payment_product_categ_ids'].ids)

            try:
                installment = self._prepare_installment()
                commission = installment['rows'][0]['installments'][0]['crate']
            except:
                commission = 0.0

            res.update({
                'categs': categs,
                'products': products,
                'commission': commission / 100,
                'validity': company.system_product_payment_validity_ok and company.system_product_payment_validity_time or 0,
            })
        return res

    @route('/my/product', type='http', auth='public', methods=['GET', 'POST'], sitemap=False, csrf=False, website=True)
    def page_product(self, **kwargs):
        #if request.env.user.share:
        #    return request.redirect('/otp')

        params = kwargs.get('', {})
        if params:
            params = json.loads(base64.b64decode(params))

        self._check_product_page(**kwargs)
        w_id = request.website.id
        website_id = int(params.get('id', w_id))
        if w_id != website_id:
            return self._redirect_product_page(website_id=website_id)

        company = request.env.company
        user = request.env.user
        companies = user.company_ids
        if len(companies) == 1 and request.website.company_id.id != user.company_id.id:
            return self._redirect_product_page(company_id=user.company_id.id)

        if company.id != request.website.company_id.id:
            return self._redirect_product_page(company_id=company.id)

        self._del()

        partner = user.partner_id if user.has_group('base.group_portal') else request.website.user_id.partner_id.sudo()
        values = self._prepare(partner=partner, company=company)
        companies = values['companies']
        if user.share:
            companies = []
        else:
            companies = companies.filtered(lambda x: x.system_product and x.id in user.company_ids.ids)

        domain = [
            ('system', '!=', False),
            ('company_id', '=', company.id),
        ]
        if partner.payment_product_categ_ids:
            domain.append(('id', 'in', partner.payment_product_categ_ids.ids))

        categs = request.env['product.category'].sudo().with_context(system=company.system).search(domain)
        products = request.env['product.template'].sudo().with_context(system=company.system).search([
            ('payment_page_ok', '=', True),
            ('categ_id', 'in', categs.ids),
        ])

        values.update({
            'success_url': '/my/payment/success',
            'fail_url': '/my/payment/fail',
            'companies': companies,
            'system': company.system,
            'subsystem': company.subsystem,
            'vat': params.get('vat'),
            'flow': 'dynamic',
            'categs': categs,
            'products': products,
            'readonly': True,
            'options': {
                'save_order_active': False,
                'listen_price_active': False,
            }
        })

        if 'values' in kwargs and isinstance(kwargs['values'], dict):
            values.update({**kwargs['values']})

        return request.render('payment_system_product.page_payment', values, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '-1'
        })

    @route('/my/product/policy', type='json', auth='public', website=True)
    def page_product_policy(self):
        token = urlparse(request.httprequest.referrer).path.rsplit('/', 1).pop()
        pid, token = request.env['res.partner'].sudo()._resolve_token(token)
        if not pid or not token:
            raise

        company = request.env.company
        partner = request.env['res.partner'].sudo().search([
            ('id', '=', pid),
            ('access_token', '=', token),
            ('company_id', '=', company.id),
        ], limit=1)
        if not partner:
            raise

        return {
            'name': partner.name,
            'vat': partner.vat,
            'address': partner.street,
            'state': partner.state_id.name,
            'country': partner.country_id.name,
            'phone': partner.mobile or partner.phone,
            'website': partner.website,
        }

    @route('/my/product/policy/send', type='json', auth='public', website=True)
    def page_product_policy_send(self):
        token = urlparse(request.httprequest.referrer).path.rsplit('/', 1).pop()
        pid, token = request.env['res.partner'].sudo()._resolve_token(token)
        if not pid or not token:
            raise

        company = request.env.company
        partner = request.env['res.partner'].sudo().search([
            ('id', '=', pid),
            ('access_token', '=', token),
            ('company_id', '=', company.id),
        ], limit=1)
        if not partner:
            raise

        if not partner.email:
            return {'error': _('Please specify an email address before proceeding.')}
        
        template = request.env.ref('payment_product.mail_policy')
        mail_server = company.mail_server_id

        context = request.env.context.copy()
        context.update({
            'company': company,
            'partner': partner,
            'tz': partner.tz,
            'lang': partner.lang,
            'server': mail_server,
            'from': mail_server.email_formatted or company.email_formatted,
        })
        template.with_context(context).send_mail(partner.id, force_send=True, email_values={
            'is_notification': True,
            'mail_server_id': mail_server.id,
        })

        return {}


    @route(['/my/payment/query/partner'], type='json', auth='public', website=True)
    def page_system_payment_query_partner(self, **kwargs):
        res = super().page_system_payment_query_partner(**kwargs)
        if 'id' in res:
            path = urlparse(request.httprequest.referrer).path
            if path.startswith('/my/product'):
                partner = request.env['res.partner'].sudo().browse(res['id'])
                res['categ_ids'] = partner.payment_product_categ_ids.ids
        return res
