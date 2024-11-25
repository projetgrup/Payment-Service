# -*- coding: utf-8 -*-
import re
import io
import json
import base64
import werkzeug
from datetime import datetime
from urllib.parse import urlparse, urlencode

from odoo import fields, http, _, SUPERUSER_ID
from odoo.http import content_disposition, request
from odoo.tools import html_escape
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import AccessError, UserError, MissingError
from odoo.addons.payment_jetcheckout.controllers.main import PayloxController as Controller

REPORT_NAMES = ['payment_jetcheckout.payment_receipt', 'payment_jetcheckout.payment_conveyance']


class PayloxSystemController(Controller):

    def _check_redirect(self, partner):
        if request.session.get('company_selected'):
            del request.session['company_selected']
            return False

        if not request.env.user.share:
            if 'cids' in request.httprequest.cookies:
                company_ids = request.httprequest.cookies['cids'].split(',')
                company_id = int(company_ids[0])
                if not company_id == request.website.company_id.id:
                    return self._redirect(company_id=company_id)
        else:
            company_id = partner.company_id.id or request.env.company.id
            if not company_id == request.website.company_id.id:
                return self._redirect(company_id=company_id)

        return False

    def _check_session(self, **kwargs):
        if kwargs.get('values', {}).get('no_session_check'):
            return
  
        if request.website.company_id.id != request.env.company.id:
            user = request.env['res.users'].sudo().search([
                ('login', '=', request.env.user.login),
                ('company_id', '=', request.website.company_id.id),
            ])

    def _check_user(self):
        path = urlparse(request.httprequest.referrer).path
        if path and '/my/payment' in path and not request.env.user.active and request.website.user_id.id != request.env.user.id:
            raise AccessError(_('Access Denied'))
        return super()._check_user()

    def _check_contactless_payment_page(self):
        if not request.env.company.payment_page_ok:
            raise werkzeug.exceptions.NotFound()
        if request.env.user.share or not request.env.user.payment_contactless_ok:
            raise werkzeug.exceptions.NotFound()

    def _check_payment_link_page(self):
        pass

    def _check_payment_page(self):
        if not request.env.company.payment_page_ok:
            raise werkzeug.exceptions.NotFound()
        if not request.env.user.share and not request.env.user.payment_page_ok:
            raise werkzeug.exceptions.NotFound()

    def _check_payment_preview_page(self):
        if request.env.user.share or not request.env.user.payment_preview_ok or not request.env.company.payment_page_ok or not request.env.company.payment_advance_ok:
            raise werkzeug.exceptions.NotFound()

    def _check_advance_page(self):
        if not request.env.company.payment_advance_ok:
            raise werkzeug.exceptions.NotFound()

    def _check_create_partner(self, **kwargs):
        if request.env.user.has_group('base.group_public'):
            return {'error': _('Only registered users can create partners.<br/>Please contact with your system administrator.')}

    def _get_parent(self, token):
        pid, token = request.env['res.partner'].sudo()._resolve_token(token)
        if not pid or not token:
            raise werkzeug.exceptions.NotFound()

        websites = request.env['website'].sudo().search([('domain', 'like', '%%%s%%' % request.httprequest.host)])
        companies = websites.mapped('company_id')
        partner = request.env['res.partner'].sudo().search([
            ('id', '=', pid), ('access_token', '=', token),
            '|',('company_id', '=', False), ('company_id', 'in', companies.ids),
        ], limit=1)
        if not partner:
            raise werkzeug.exceptions.NotFound()

        self._set('partner', partner.id)
        return partner
    
    def _get_website_partner(self):
        user = request.env.user
        if user.has_group('base.group_portal'):
            return user.partner_id
        else:
            return request.website.sudo().user_id.partner_id 

    def _get_tx_values(self, **kwargs):
        vals = super()._get_tx_values(**kwargs)
        ids = kwargs.get('payments', [])
        if ids:
            vals.update({'jetcheckout_item_ids': [(6, 0, ids)]})
        if request.env.company.system:
            vals.update({'jetcheckout_payment_ok': False})

        tag = kwargs.get('payment_tag', False)
        if tag:
            vals.update({'paylox_item_tag_id': tag})

        sale_ref = kwargs.get('sale_ref', False)
        if sale_ref:
            vals.update({'paylox_sale_ref': sale_ref})
        return vals

    def _process(self, **kwargs):
        url, tx, status = super()._process(**kwargs)
        if not status and (tx.company_id.system or tx.partner_id.system):
            status = True
            path = urlparse(tx.jetcheckout_url_address).path
            if (path.startswith('/p/')):
                path = tx.partner_id._get_share_url()
            else:
                path = '/my/payment/result'
            url = '%s?=%s' % (path, kwargs.get('order_id'))
        return url, tx, status

    def _prepare(self, **kwargs):
        res = super()._prepare(**kwargs)
        res['companies'] = request.website._get_companies()
        return res

    def _prepare_system(self, company, system, partner, transaction, options={}):
        currency = company.currency_id
        acquirer = self._get_acquirer(False)
        installment_type = self._get_type()
        campaign = transaction.jetcheckout_campaign_name if transaction else partner.campaign_id.name if partner else ''
        card_family = self._get_card_family(acquirer=acquirer, campaign=campaign)
        token = partner._get_token()
        tags = partner._get_tags()
        websites = request.website._get_companies()
        companies = partner._get_companies().filtered(lambda x: x.id in websites.ids)
        language = request.env['res.lang']._lang_get(request.env.lang)

        types = self._get_payment_types(acquirer=acquirer)
        shopping_credits = []
        wallets = []
        transfers = []
        for ptype in types:
            if ptype['code'] == 'credit':
                shopping_credits = self._prepare_credit(acquirer=acquirer, currency=currency)
            elif ptype['code'] == 'wallet':
                wallets = self._prepare_wallet(acquirer=acquirer)
            elif ptype['code'] == 'transfer':
                transfers = self._prepare_wiretransfer(acquirer=acquirer)

        if options.get('no_compute_payment_tags'):
            payments, payment_tags = False, False
        else:
            payments, payment_tags = partner._get_payments()
            currency = payments.mapped('currency_id') or currency
            if len(currency) > 1:
                raise UserError(_('Payment items must share one common currency'))
            if payment_tags and payment_tags[0].campaign_id:
                campaign = payment_tags[0].campaign_id.name

        return {
            'ok': True,
            'partner': partner,
            'partner_name': partner.name,
            'tags': tags,
            'company': company,
            'companies': companies,
            'website': request.website,
            'footer': request.website.payment_footer,
            'user': not request.env.user.share,
            'acquirer': acquirer,
            'campaign': campaign,
            'payments': payments,
            'language': language,
            'payment_tags': payment_tags,
            'card_family': card_family,
            'success_url': '/payment/card/success',
            'fail_url': '/payment/card/fail',
            'tx': transaction,
            'system': system,
            'token': token,
            'types': types,
            'shopping_credits': shopping_credits,
            'wallets': wallets,
            'transfers': transfers,
            'currency': currency,
            'currencies': currency,
            'installment_type': installment_type,
            'no_terms': not acquirer.provider == 'jetcheckout' or acquirer.jetcheckout_no_terms,
        }

    @http.route('/web/system/load', type='json', auth='user')
    def action_load(self, cids=None, action=None, menu_id=None):
        company = request.env['res.company'].sudo().browse(int(cids and str(cids).split(',', 1)[0] or request.env.company.id))
        system = company.system
        state = {}

        if system and not action and not menu_id:
            state['menu_id'] = request.env.ref('payment_%s.menu_payment' % system).id
            return state

        if action:
            state['action'] = action
            if system:
                action_data = request.env['ir.model.data'].sudo().search([('model', '=', 'ir.actions.act_window'), ('res_id', '=', action)], limit=1)
                action_xmlid = action_data.complete_name if action_data else None
                if action_xmlid:
                    match = re.match(r'^payment_(.+)\.action_(.+)$', action_xmlid)
                    if match:
                        action_xmlid = f'payment_{system}.action_{match.group(2)}'
                        if not request.env.ref(action_xmlid, False):
                            action_xmlid = request.env['ir.model.data'].sudo().search([('model', '=', 'ir.actions.act_window'), ('res_id', '=', action)], limit=1).complete_name
                    state['action'] = request.env.ref(action_xmlid).id

        if menu_id:
            state['menu_id'] = menu_id
            if system:
                menu_data = request.env['ir.model.data'].sudo().search([('model', '=', 'ir.ui.menu'), ('res_id', '=', menu_id)], limit=1)
                menu_xmlid = menu_data.complete_name if menu_data else None
                if menu_xmlid:
                    match = re.match(r'^payment_(.+)\.menu_(.+)$', menu_xmlid)
                    if match:
                        menu_xmlid = f'payment_{system}.menu_{match.group(2)}'
                    state['menu_id'] = request.env.ref(menu_xmlid).id

        return state

    @http.route('/p/<token>', type='http', auth='public', methods=['GET'], csrf=False, sitemap=False, website=True)
    def page_system_link(self, token, **kwargs):
        self._check_payment_link_page()
        partner = self._get_parent(token)
        transaction = None
        if '' in kwargs:
            txid = re.split(r'\?|%3F', kwargs[''])[0]
            transaction = request.env['payment.transaction'].sudo().search([('jetcheckout_order_id', '=', txid)], limit=1)
            if not transaction:
                raise werkzeug.exceptions.NotFound()

        company = partner.company_id or request.website.company_id or request.env.company
        if not company == request.env.company:
            website = request.env['website'].sudo().search([('company_id', '=', company.id)], limit=1)
            if not website:
                raise werkzeug.exceptions.NotFound()

            website._force()
            return request.redirect(request.httprequest.url)

        self._del()

        system = company.system or partner.system or 'jetcheckout_system'
        values = self._prepare_system(company, system, partner, transaction)
        return request.render('payment_%s.page_payment' % system, values, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '-1'
        })

    @http.route('/p/<token>/<int:pid>', type='http', auth='public', methods=['POST'], csrf=False, sitemap=False, website=True)
    def page_system_link_file(self, token, pid, **kwargs):
        partner = self._get_parent(token)
        payment = request.env['payment.item'].sudo().browse(pid)
        if not payment.parent_id.id == partner.id or payment.paid:
            raise werkzeug.exceptions.NotFound()

        pdf = payment.file
        if not pdf:
            raise werkzeug.exceptions.NotFound()

        pdf = base64.b64decode(pdf)
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'attachment; filename="%s.pdf"' % html_escape(payment.description)),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route(['/p/privacy'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_privacy_policy(self):
        return request.website.payment_privacy_policy

    @http.route(['/p/agreement'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_sale_agreement(self):
        return request.website.payment_sale_agreement

    @http.route(['/p/membership'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_membership_agreement(self):
        return request.website.payment_membership_agreement

    @http.route(['/p/contact'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_contact_page(self):
        return request.website.payment_contact_page

    @http.route(['/p/company'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_company(self, cid):
        if cid == request.env.company.id:
            return False

        token = urlparse(request.httprequest.referrer).path.rsplit('/', 1).pop()
        id, token = request.env['res.partner'].sudo()._resolve_token(token)
        if not id or not token:
            return False

        website = request.env['website'].sudo().search([
            ('domain', '=', request.website.domain),
            ('company_id', '=', cid)
        ], limit=1)
        if not website:
            return False

        partner = request.env['res.partner'].sudo().search([
            ('id', '=', id),
            ('access_token', '=', token),
            ('company_id', '=', request.env.company.id),
        ], limit=1)
        if not partner:
            return False

        partner = request.env['res.partner'].sudo().search([
            ('vat', '!=', False),
            ('vat', '=', partner.vat),
            ('company_id', '=', cid),
        ], limit=1)
        if not partner:
            return False

        website._force()
        return partner._get_token()

    @http.route(['/p/company/<int:id>/logo'], type='http', auth='public')
    def page_system_link_company_image(self, id):
        return request.env['ir.http'].sudo()._content_image(xmlid=None, model='res.company', res_id=id, field='logo', filename_field='name', unique=None, filename=None, mimetype=None, download=None, width=0, height=0, crop=False, quality=0, access_token=None)

    @http.route(['/p/tag'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_tag(self, tid):
        token = urlparse(request.httprequest.referrer).path.rsplit('/', 1).pop()
        id, token = request.env['res.partner'].sudo()._resolve_token(token)
        if not id or not token:
            return False

        partner = request.env['res.partner'].sudo().search([
            ('id', '=', id),
            ('access_token', '=', token),
            ('company_id', '=', request.env.company.id),
        ], limit=1)
        if not partner:
            return False

        if tid in partner.category_id.ids:
            return False

        partner = request.env['res.partner'].sudo().search([
            ('vat', '!=', False),
            ('vat', '=', partner.vat),
            ('category_id', 'in', [tid]),
            ('company_id', '=', request.env.company.id),
        ], limit=1)
        if not partner:
            return False

        return partner._get_token()

    @http.route(['/p/due'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_due(self, items, tag=False):
        amounts = dict(items)
        items = request.env['payment.item'].sudo().browse([i[0] for i in items])
        return items.with_context(amounts=amounts, tag=tag).get_due()

    @http.route(['/p/due/tag'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_due_tag(self, tag=False):
        token = urlparse(request.httprequest.referrer).path.rsplit('/', 1).pop()
        id, token = request.env['res.partner'].sudo()._resolve_token(token)
        if not id or not token:
            raise

        company = request.env.company
        partner = request.env['res.partner'].sudo().search([
            ('id', '=', id),
            ('access_token', '=', token),
            ('company_id', '=', company.id),
        ], limit=1)
        if not partner:
            raise

        payment_tags = company.sudo().payment_page_campaign_tag_ids
        payment_tag = payment_tags.filtered(lambda x: x.id == tag)
        payment_tag_filter = []

        if payment_tag and payment_tag.campaign_id:
            payment_tag_filter.append(('tag', 'in', payment_tag.line_ids.mapped('name')))
        else:
            payment_tag_filter.append(('tag', 'not in', payment_tags.mapped('line_ids.name')))

        payments = []
        items = request.env['payment.item'].sudo().search([
            ('parent_id', '=', partner.id),
            ('paid', '=', False),
        ] + payment_tag_filter, order='date,amount')
        for item in items:
            if item.currency_id:
                currency = {
                    'id': item.currency_id.id,
                    'decimal': item.currency_id.decimal_places,
                    'name': item.currency_id.name,
                    'position': item.currency_id.position,
                    'symbol': item.currency_id.symbol, 
                }
            else:
                currency = False

            payments.append({
                'id': item.id,
                'date': item.date,
                'due_date': item.due_date,
                'amount': item.amount,
                'manual': item.manual,
                'advance': item.advance,
                'residual_amount': item.residual_amount,
                'description': item.description or '',
                'file': item.file,
                'token': token,
                'currency': currency,
            })

        company = {
            'campaign': payment_tag and payment_tag.campaign_id.name,
            'due_base': company.payment_page_due_base,
            'due_ok': company.payment_page_due_ok and not (payment_tag and payment_tag.campaign_id),
            'advance_ok': company.payment_page_advance_ok,
        }
        return payments, company

    @http.route(['/p/item/add'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_item_add(self, **kwargs):
        token = urlparse(request.httprequest.referrer).path.rsplit('/', 1).pop()
        id, token = request.env['res.partner'].sudo()._resolve_token(token)
        if not id or not token:
            raise

        company = request.env.company
        partner = request.env['res.partner'].sudo().search([
            ('id', '=', id),
            ('access_token', '=', token),
            ('company_id', '=', company.id),
        ], limit=1)
        if not partner:
            raise

        payment_tagv = kwargs.get('tag', False)
        payment_tags = company.sudo().payment_page_campaign_tag_ids
        payment_tag = payment_tags.filtered(lambda x: x.name == payment_tagv)
        payment_tag_filter = []

        if len(payment_tag) == 1 and payment_tag.campaign_id:
            payment_tag_filter.append(('tag', 'in', payment_tag.line_ids.mapped('name')))
        else:
            payment_tag_filter.append(('tag', 'not in', payment_tags.mapped('line_ids.name')))

        payment_date = kwargs.get('date', False)
        if payment_date:
            payment_date = datetime.strptime(payment_date, '%d-%m-%Y')

        request.env['payment.item'].sudo().create({
            'parent_id': partner.id,
            'tag': payment_tagv,
            'date': payment_date,
            'manual': True,
            'amount': kwargs.get('amount', False),
            'description': kwargs.get('desc', False),
        })

        payments = []
        items = request.env['payment.item'].sudo().search([
            ('parent_id', '=', partner.id),
            ('paid', '=', False),
        ] + payment_tag_filter, order='date,amount')
        for item in items:
            if item.currency_id:
                currency = {
                    'id': item.currency_id.id,
                    'decimal': item.currency_id.decimal_places,
                    'name': item.currency_id.name,
                    'position': item.currency_id.position,
                    'symbol': item.currency_id.symbol, 
                }
            else:
                currency = False

            payments.append({
                'id': item.id,
                'date': item.date,
                'due_date': item.due_date,
                'amount': item.amount,
                'manual': item.manual,
                'advance': item.advance,
                'residual_amount': item.residual_amount,
                'description': item.description,
                'file': item.file,
                'token': token,
                'currency': currency,
            })

        company = request.env.company
        company = {
            'campaign': payment_tag and payment_tag.campaign_id.name or False,
            'advance_ok': company.payment_page_advance_ok,
            'due_base': company.payment_page_due_base,
            'due_ok': payment_tag and not payment_tag.campaign_id and company.payment_page_due_ok or False,
        }
        return payments, company

    @http.route(['/p/item/remove'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_item_remove(self, **kwargs):
        token = urlparse(request.httprequest.referrer).path.rsplit('/', 1).pop()
        id, token = request.env['res.partner'].sudo()._resolve_token(token)
        if not id or not token:
            raise

        company = request.env.company
        partner = request.env['res.partner'].sudo().search([
            ('id', '=', id),
            ('access_token', '=', token),
            ('company_id', '=', company.id),
        ], limit=1)
        if not partner:
            raise

        payment_tagv = kwargs.get('tag', False)
        payment_tags = company.sudo().payment_page_campaign_tag_ids
        payment_tag = payment_tags.filtered(lambda x: x.name == payment_tagv)
        payment_tag_filter = []

        request.env['payment.item'].sudo().search([
            ('id', '=', kwargs.get('pid', 0)),
            ('parent_id', '=', partner.id),
            ('paid_amount', '=', 0),
            ('manual', '=', True),
        ] + payment_tag_filter).unlink()

        payments = []
        items = request.env['payment.item'].sudo().search([
            ('parent_id', '=', partner.id),
            ('paid', '=', False),
        ] + payment_tag_filter, order='date,amount')

        for item in items:
            if item.currency_id:
                currency = {
                    'id': item.currency_id.id,
                    'decimal': item.currency_id.decimal_places,
                    'name': item.currency_id.name,
                    'position': item.currency_id.position,
                    'symbol': item.currency_id.symbol, 
                }
            else:
                currency = False

            payments.append({
                'id': item.id,
                'date': item.date,
                'due_date': item.due_date,
                'amount': item.amount,
                'manual': item.manual,
                'advance': item.advance,
                'residual_amount': item.residual_amount,
                'description': item.description,
                'file': item.file,
                'token': token,
                'currency': currency,
            })

        company = request.env.company
        company = {
            'campaign': payment_tag and payment_tag.campaign_id.name or False,
            'due_base': company.payment_page_due_base,
            'due_ok': company.payment_page_due_ok,
            'advance_ok': company.payment_page_advance_ok,
        }
        return payments, company

    @http.route(['/p/advance/add'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_advance_add(self, amount, tag=False):
        if not request.env.company.payment_page_advance_ok:
            raise

        token = urlparse(request.httprequest.referrer).path.rsplit('/', 1).pop()
        id, token = request.env['res.partner'].sudo()._resolve_token(token)
        if not id or not token:
            raise

        company = request.env.company
        partner = request.env['res.partner'].sudo().search([
            ('id', '=', id),
            ('access_token', '=', token),
            ('company_id', '=', company.id),
        ], limit=1)
        if not partner:
            raise

        payment_tags = company.sudo().payment_page_campaign_tag_ids
        payment_tag = payment_tags.filtered(lambda x: x.name == tag)
        payment_tag_filter = []

        if len(payment_tag) == 1 and payment_tag.campaign_id:
            payment_tag_filter.append(('tag', 'in', payment_tag.line_ids.mapped('name')))
        else:
            payment_tag_filter.append(('tag', 'not in', payment_tags.mapped('line_ids.name')))

        item = request.env['payment.item'].sudo().search([
            ('parent_id', '=', partner.id),
            ('advance', '=', True),
            ('paid', '=', False),
        ] + payment_tag_filter, limit=1)
        if item:
            item.write({
                'date': fields.Date.today(),
                'amount': item.amount + amount,
            })
        else:
            request.env['payment.item'].sudo().create({
                'parent_id': partner.id,
                'amount': amount,
                'tag': tag,
                'advance': True,
                'description': _('Advance Payment'),
            })

        payments = []
        items = request.env['payment.item'].sudo().search([
            ('parent_id', '=', partner.id),
            ('paid', '=', False),
        ] + payment_tag_filter, order='date,amount')
        for item in items:
            if item.currency_id:
                currency = {
                    'id': item.currency_id.id,
                    'decimal': item.currency_id.decimal_places,
                    'name': item.currency_id.name,
                    'position': item.currency_id.position,
                    'symbol': item.currency_id.symbol, 
                }
            else:
                currency = False

            payments.append({
                'id': item.id,
                'date': item.date,
                'due_date': item.due_date,
                'amount': item.amount,
                'manual': item.manual,
                'advance': item.advance,
                'residual_amount': item.residual_amount,
                'description': item.description,
                'file': item.file,
                'token': token,
                'currency': currency,
            })

        company = request.env.company
        company = {
            'campaign': payment_tag and payment_tag.campaign_id.name or False,
            'advance_ok': company.payment_page_advance_ok,
            'due_base': company.payment_page_due_base,
            'due_ok': payment_tag and not payment_tag.campaign_id and company.payment_page_due_ok or False,
        }
        return payments, company

    @http.route(['/p/advance/remove'], type='json', auth='public', website=True, csrf=False)
    def page_system_link_advance_remove(self, pid, tag=False):
        token = urlparse(request.httprequest.referrer).path.rsplit('/', 1).pop()
        id, token = request.env['res.partner'].sudo()._resolve_token(token)
        if not id or not token:
            raise

        company = request.env.company
        partner = request.env['res.partner'].sudo().search([
            ('id', '=', id),
            ('access_token', '=', token),
            ('company_id', '=', company.id),
        ], limit=1)
        if not partner:
            raise

        payment_tags = company.sudo().payment_page_campaign_tag_ids
        payment_tag = payment_tags.filtered(lambda x: x.name == tag)
        payment_tag_filter = []

        request.env['payment.item'].sudo().search([
            ('id', '=', pid),
            ('parent_id', '=', partner.id),
            ('paid_amount', '=', 0)
        ] + payment_tag_filter).unlink()

        payments = []
        items = request.env['payment.item'].sudo().search([
            ('parent_id', '=', partner.id),
            ('paid', '=', False),
        ] + payment_tag_filter, order='date,amount')

        for item in items:
            if item.currency_id:
                currency = {
                    'id': item.currency_id.id,
                    'decimal': item.currency_id.decimal_places,
                    'name': item.currency_id.name,
                    'position': item.currency_id.position,
                    'symbol': item.currency_id.symbol, 
                }
            else:
                currency = False

            payments.append({
                'id': item.id,
                'date': item.date,
                'due_date': item.due_date,
                'amount': item.amount,
                'manual': item.manual,
                'advance': item.advance,
                'residual_amount': item.residual_amount,
                'description': item.description,
                'file': item.file,
                'token': token,
                'currency': currency,
            })

        company = request.env.company
        company = {
            'campaign': payment_tag and payment_tag.campaign_id.name or False,
            'due_base': company.payment_page_due_base,
            'due_ok': company.payment_page_due_ok,
            'advance_ok': company.payment_page_advance_ok,
        }
        return payments, company

    @http.route('/my/advance', type='http', auth='public', methods=['GET', 'POST'], sitemap=False, csrf=False, website=True)
    def page_system_advance(self, **kwargs):
        params = kwargs.get('', {})
        if params:
            params = json.loads(base64.b64decode(params))

        if request.env.user.share and not 'id' in params:
            raise werkzeug.exceptions.NotFound()

        w_id = request.website.id
        website_id = int(params.get('id', w_id))
        if w_id != website_id:
            return self._redirect(website_id=website_id)

        partner = self._get_website_partner()
        redirect = self._check_redirect(partner)
        if redirect:
            return redirect

        self._check_advance_page()
        self._del()

        if 'currency' in params and isinstance(params['currency'], str) and len(params['currency']) == 3:
            currency = request.env['res.currency'].sudo().search([('name', '=', params['currency'])], limit=1)
        else:
            currency = None

        user = request.env.user
        company = request.env.company
        values = self._prepare(partner=partner, company=company, currency=currency)
        companies = values['companies']
        if user.share:
            companies = []
        else:
            companies = companies.filtered(lambda x: x.payment_advance_ok and x.id in user.company_ids.ids)

        values.update({
            'success_url': '/my/payment/success',
            'fail_url': '/my/payment/fail',
            'companies': companies,
            'system': company.system,
            'subsystem': company.subsystem,
            'vat': params.get('vat'),
            'flow': 'dynamic',
            'advance': True,
            'readonly': user.share and company.payment_advance_amount_readonly,
        })

        if 'values' in kwargs and isinstance(kwargs['values'], dict):
            values.update({**kwargs['values']})

        try:
            values.update({'amount': float(params['amount'])})
        except:
            pass

        return request.render('payment_jetcheckout_system.page_payment', values, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '-1'
        })

    @http.route('/my/payment/preview', type='http', auth='public', methods=['GET'], sitemap=False, csrf=False, website=True)
    def page_system_payment_preview(self, **kwargs):
        partner = self._get_website_partner()
        redirect = self._check_redirect(partner)
        if redirect:
            return redirect

        self._check_payment_preview_page()
        self._del()

        company = request.env.company
        values = self._prepare(company=company)
        values.update({
            'system': company.system,
            'subsystem': company.subsystem,
        })

        params = kwargs.get('', {})
        if params:
            params = json.loads(base64.b64decode(params))

        if 'values' in kwargs and isinstance(kwargs['values'], dict):
            values.update({**kwargs['values']})

        try:
            values.update({'amount': float(params['amount'])})
        except:
            pass

        return request.render('payment_jetcheckout_system.page_payment_preview', values, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '-1'
        })

    @http.route('/m/payment', type='http', auth='public', methods=['GET', 'POST'], sitemap=False, csrf=False, website=True)
    def page_system_contactless_payment(self, **kwargs):
        if not request.env.user.has_group('base.group_user'):
            raise werkzeug.exceptions.NotFound()

        if not kwargs.get('values', {}).get('no_redirect'):
            redirect = self._check_redirect(request.env.user.partner_id)
            if redirect:
                return redirect

        self._check_contactless_payment_page()

        params = kwargs.get('', {})
        if params:
            params = json.loads(base64.b64decode(params))

        partner = None
        company = request.env.company
        if 'pid' in params:
            partner = self._get_parent(params['pid'])
        elif 'vat' in params and isinstance(params['vat'], str) and 9 < len(params['vat']) < 14:
            partner = request.env['res.partner'].sudo().search([
                ('vat', '!=', False),
                ('vat', '=', params['vat']),
                ('company_id', '=', company.id),
                ('system', '=', company.system)
            ])
            if len(partner) != 1:
                partner = None
        elif company.payment_page_flow == 'dynamic':
            partner = request.website.user_id.partner_id.sudo()

        if not partner:
            partner = self._get_partner()

        if 'currency' in params and isinstance(params['currency'], str) and len(params['currency']) == 3:
            currency = request.env['res.currency'].sudo().search([('name', '=', params['currency'])], limit=1)
        else:
            currency = None

        self._del()
        self._set('partner', partner.id)

        values = self._prepare(partner=partner, company=company, currency=currency)

        link_params = json.dumps({
            'id': request.website.id,
            'currency': values['currency']['name'],
            'vat': values['partner']['vat'],
            'amount': float(params.get('amount', 0)),
        })
        link = '%s?%s' % (request.httprequest.url, urlencode({'': base64.b64encode(link_params.encode('utf-8'))}))

        values.update({
            'success_url': '/my/payment/success',
            'fail_url': '/my/payment/fail',
            'system': company.system,
            'subsystem': company.subsystem,
            'flow': company.payment_page_flow,
            'vat': params.get('vat'),
            'link': link,
        })

        if 'values' in kwargs and isinstance(kwargs['values'], dict):
            values.update({**kwargs['values']})

        try:
            values.update({'amount': float(params['amount'])})
        except:
            pass

        return request.render('payment_jetcheckout_system.page_contactless_payment', values, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '-1'
        })

    @http.route('/my/payment', type='http', auth='public', methods=['GET', 'POST'], sitemap=False, csrf=False, website=True)
    def page_system_payment(self, **kwargs):
        #request.uid = 62
        if request.env.user.has_group('base.group_public'):
            raise werkzeug.exceptions.NotFound()

        if not kwargs.get('values', {}).get('no_redirect'):
            redirect = self._check_redirect(request.env.user.partner_id)
            if redirect:
                return redirect

        self._check_payment_page()

        params = kwargs.get('', {})
        if params:
            params = json.loads(base64.b64decode(params))

        partner = None
        company = request.env.company
        if 'pid' in params:
            partner = self._get_parent(params['pid'])
        elif 'vat' in params and isinstance(params['vat'], str) and 9 < len(params['vat']) < 14:
            partner = request.env['res.partner'].sudo().search([
                ('vat', '!=', False),
                ('vat', '=', params['vat']),
                ('company_id', '=', company.id),
                ('system', '=', company.system)
            ])
            if len(partner) != 1:
                partner = None
        elif company.payment_page_flow == 'dynamic':
            partner = request.website.user_id.partner_id.sudo()

        if not partner:
            partner = self._get_partner()

        if 'currency' in params and isinstance(params['currency'], str) and len(params['currency']) == 3:
            currency = request.env['res.currency'].sudo().search([('name', '=', params['currency'])], limit=1)
        else:
            currency = None

        self._del()
        self._set('partner', partner.id)

        values = self._prepare(partner=partner, company=company, currency=currency)
        values.update({
            'success_url': '/my/payment/success',
            'fail_url': '/my/payment/fail',
            'system': company.system,
            'subsystem': company.subsystem,
            'flow': company.payment_page_flow,
            'vat': params.get('vat'),
        })

        if 'values' in kwargs and isinstance(kwargs['values'], dict):
            values.update({**kwargs['values']})

        try:
            values.update({'amount': float(params['amount'])})
        except:
            pass

        return request.render('payment_jetcheckout_system.page_payment', values, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '-1'
        })

    @http.route('/my/payment/link', type='http', auth='public', methods=['GET'], sitemap=False, csrf=False, website=True)
    def page_system_payment_link(self, **kwargs):
        if not kwargs.get('values', {}).get('no_redirect'):
            redirect = self._check_redirect(request.env.user.partner_id)
            if redirect:
                return redirect

        self._check_payment_page()

        params = kwargs.get('', {})
        if params:
            params = json.loads(base64.b64decode(params))

        partner = None
        company = request.env.company
        if 'pid' in params:
            partner = self._get_parent(params['pid'])
        elif 'vat' in params and isinstance(params['vat'], str) and 9 < len(params['vat']) < 14:
            partner = request.env['res.partner'].sudo().search([
                ('vat', '!=', False),
                ('vat', '=', params['vat']),
                ('company_id', '=', company.id),
                ('system', '=', company.system)
            ])
            if len(partner) != 1:
                partner = None
        else:
            partner = request.website.user_id.partner_id.sudo()

        if not partner:
            partner = self._get_partner()

        if 'currency' in params and isinstance(params['currency'], str) and len(params['currency']) == 3:
            currency = request.env['res.currency'].sudo().search([('name', '=', params['currency'])], limit=1)
        else:
            currency = None

        self._del()
        self._set('partner', partner.id)

        values = self._prepare(partner=partner, company=company, currency=currency)
        values.update({
            'success_url': '/my/payment/success',
            'fail_url': '/my/payment/fail',
            'system': company.system,
            'subsystem': company.subsystem,
            'vat': params.get('vat'),
            'flow': 'dynamic',
            'readonly': True,
        })

        return request.render('payment_jetcheckout_system.page_payment', values, headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '-1'
        })

    @http.route('/my/payment/<token>', type='http', auth='public', methods=['GET'], sitemap=False, website=True)
    def page_system_payment_login(self, token, **kwargs):
        partner = self._get_parent(token)
        redirect = self._check_redirect(partner)
        if redirect:
            return redirect

        self._check_payment_page()

        self._del()
        self._set('partner', partner.id)

        if partner.is_portal:
            if request.env.user.has_group('base.group_public'):
                user = partner.users_id
                request.session.authenticate(request.db, user.login, {'token': token})
            return request.render('payment_jetcheckout_system.page_login', {'token': token})
        else:
            return werkzeug.utils.redirect('/p/%s' % token)

    @http.route(['/my/payment/company'], type='json', auth='public', website=True, csrf=False)
    def page_system_page_company(self, cid):
        if request.env.user._is_public():
            return False

        if cid == request.env.company.id:
            return False
            #if request.session.get('company_selected'):
            #    return False

        else:
            website = request.env['website'].sudo().search([
                ('domain', '=', request.website.domain),
                ('company_id', '=', cid)
            ], limit=1)
            if not website:
                return False
            website._force()

            if not request.env.user._is_internal():
                user = request.env['res.users'].sudo().search([
                    ('login', '=', request.env.user.login),
                    ('company_id', '=', website.company_id.id),
                ])
                request.session.authenticate(request.db, user.login, {'token': user.partner_id._get_token(), 'company': website.company_id.id})
                self._set('partner', user.partner_id.id)

        request.session['company_selected'] = True
        return True

    @http.route(['/my/payment/company/<int:id>/logo'], type='http', auth='public')
    def page_system_page_company_image(self, id):
        return request.env['ir.http'].sudo()._content_image(xmlid=None, model='res.company', res_id=id, field='logo', filename_field='name', unique=None, filename=None, mimetype=None, download=None, width=0, height=0, crop=False, quality=0, access_token=None)

    @http.route(['/my/payment/success', '/my/payment/fail'], type='http', auth='public', methods=['POST'], csrf=False, sitemap=False, save_session=False)
    def page_system_payment_return(self, **kwargs):
        kwargs['result_url'] = '/my/payment/result'
        url, tx, status = self._process(**kwargs)
        if not status and tx.jetcheckout_order_id:
            url += '?=%s' % tx.jetcheckout_order_id
        return werkzeug.utils.redirect(url)

    @http.route('/my/payment/result', type='http', auth='public', methods=['GET'], sitemap=False, website=True)
    def page_system_payment_result(self, **kwargs):
        values = self._prepare()
        if '' in kwargs:
            txid = re.split(r'\?|%3F', kwargs[''])[0]
            values['tx'] = request.env['payment.transaction'].sudo().search([('jetcheckout_order_id', '=', txid)], limit=1)
        else:
            txid = self._get('tx', 0)
            values['tx'] = request.env['payment.transaction'].sudo().browse(txid)
        self._del()
        return request.render('payment_jetcheckout_system.page_result', values)

    @http.route([
        '/my/payment/transaction',
        '/my/payment/transaction/page/<int:page>',
        '/p/<token>/transaction',
        '/p/<token>/transaction/page/<int:page>',
        ], type='http', auth='public', methods=['GET'], website=True)
    def page_system_payment_transaction(self, token=None, page=0, **kwargs):
        user = request.env.user
        if token:
            partner = self._get_parent(token)
            url_payment = '/p/%s' % token
        else:
            if user.has_group('base.group_public'):
                raise AccessError(_('Please login before continue.'))
            partner = self._get_partner()
            url_payment = '/my/payment'

        partner_commercial = partner.commercial_partner_id
        partner_contact = partner if partner.parent_id else False

        acquirer = self._get_acquirer()
        values = {
            'company': request.env.company,
            'partner': partner_commercial,
            'partner_name': partner_commercial.name,
            'contact': partner_contact,
            'acquirer': acquirer,
            'token': token,
            'user': not user.share,
            'url_payment': url_payment,
        }

        if user.group_own_transaction:
            domain = [
                ('partner_id', '=', partner and partner.id or False),
            ]
        else:
            domain = [
                '|',
                ('partner_id', '=', partner and partner.commercial_partner_id.id or False),
                ('partner_id.parent_id', '=', partner and partner.commercial_partner_id.id or False),
            ]

        txs = request.env['payment.transaction'].sudo().search(domain)

        step = 10
        pager = request.website.pager(url='', total=len(txs), page=page, step=step, scope=7, url_args=kwargs)
        offset = pager['offset']
        txs = txs[offset: offset + step]
        values.update({
            'pager': pager,
            'txs': txs,
            'date_format': 'DD-MM-YYYY'
        })
        if request.env.lang:
            lang = request.env.lang
            values.update({
                'date_locale': lang[:2],
            })
        return request.render('payment_jetcheckout_system.page_transaction', values)

    @http.route([
        '/my/payment/transaction/list',
        '/p/<token>/transaction/list',
    ], type='json', auth='public', website=True)
    def page_system_payment_transaction_list(self, token=None, **kwargs):
        date_format = kwargs.get('format')
        if not date_format:
            return {'error': _('Date format cannot be empty')}

        user = request.env.user
        if token:
            partner = self._get_parent(token)
        else:
            if user.has_group('base.group_public'):
                raise AccessError(_('Please login before continue.'))
            partner = self._get_partner()

        if user.group_own_transaction:
            domain = [
                ('partner_id', '=', partner and partner.id or False),
            ]
        else:
            domain = [
                '|',
                ('partner_id', '=', partner and partner.commercial_partner_id.id or False),
                ('partner_id.parent_id', '=', partner and partner.commercial_partner_id.id or False),
            ]

        date_format = date_format.replace('DD', '%d').replace('MM', '%m').replace('YYYY', '%Y')
        if kwargs.get('start'):
            date_start = datetime.strptime(kwargs['start'], date_format)
            domain.append(('create_date', '>=', date_start))
        if kwargs.get('end'):
            date_end = datetime.strptime(kwargs['end'], date_format)
            domain.append(('create_date', '<=', date_end))
        if kwargs.get('state'):
            domain.append(('state', 'in', kwargs['state']))
        txs = request.env['payment.transaction'].sudo().search(domain)

        step = 10    
        pager = request.website.pager(url='', total=len(txs), page=kwargs.get('page', 1), step=step, scope=7)
        offset = pager['offset']
        txs = txs[offset: offset + step]
        pager = request.env['ir.ui.view'].sudo()._render_template('website.pager', {'pager': pager})
        page = request.env['ir.ui.view'].sudo()._render_template('payment_jetcheckout_system.page_transaction_list', {'txs': txs, 'token': token})

        return {
            'pager': pager,
            'page': page,
        }

    @http.route([
        '/my/payment/transaction/download',
        '/p/<token>/transaction/download',
    ], type='http', auth='public', methods=['GET'], sitemap=False, website=True)
    def page_system_payment_transaction_download(self, token=None, **kwargs):
        date_format = kwargs.get('format')
        if not date_format:
            return {'error': _('Date format cannot be empty')}

        user = request.env.user
        if token:
            partner = self._get_parent(token)
        else:
            if user.has_group('base.group_public'):
                raise AccessError(_('Please login before continue.'))
            partner = self._get_partner()

        if user.group_own_transaction:
            domain = [
                ('partner_id', '=', partner and partner.id or False),
            ]
        else:
            domain = [
                '|',
                ('partner_id', '=', partner and partner.commercial_partner_id.id or False),
                ('partner_id.parent_id', '=', partner and partner.commercial_partner_id.id or False),
            ]

        date_format = date_format.replace('DD', '%d').replace('MM', '%m').replace('YYYY', '%Y')
        if kwargs.get('start'):
            date_start = datetime.strptime(kwargs['start'], date_format)
            domain.append(('create_date', '>=', date_start))
        if kwargs.get('end'):
            date_end = datetime.strptime(kwargs['end'], date_format)
            domain.append(('create_date', '<=', date_end))
        if kwargs.get('state'):
            domain.append(('state', 'in', kwargs['state'].split(',')))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        headers = {
            'create_date': _('Date'),
            'reference': _('Reference'),
            'jetcheckout_card_name': _('Card Holder Name'),
            'jetcheckout_card_number': _('Card Number'),
            'jetcheckout_payment_amount': _('Payment Amount'),
            'jetcheckout_installment_count': _('Installment Count'),
            'jetcheckout_customer_amount': _('Commission Amount'),
            'state': _('State'),
            'state_message': _('Message'),
        }
        date_format = workbook.add_format({'num_format': kwargs['format']})
        for i, col in enumerate(headers.values()):
            worksheet.write(0, i, col)

        txs = request.env['payment.transaction'].sudo().search_read(domain, list(headers.keys()))

        row = 0
        for tx in txs:
            row += 1
            for i, key in enumerate(headers.keys()):
                if key == 'create_date':
                    worksheet.write_datetime(row, i, tx[key], date_format)
                else:
                    worksheet.write(row, i, tx[key])
        workbook.close()
        headers = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition('%s.xlsx' % _('Transactions')))
        ]
        return request.make_response(output.getvalue(), headers=headers)

    @http.route(['/my/payment/query/partner'], type='json', auth='public', website=True)
    def page_system_payment_query_partner(self, **kwargs):
        partner = request.env['res.partner'].sudo().search([
            ('vat', '!=', False),
            ('vat', '=', kwargs.get('vat')),
            ('company_id', '=', request.env.company.id),
        ], limit=1)

        if not partner:
            return {
                'vat': '11111111111',
            }
        else:
            values = partner.read([
                'id',
                'vat',
                'name',
                'phone',
                'email',
                'city',
                'street',
                'country_id',
                'state_id',
            ])[0]

            path = urlparse(request.httprequest.referrer).path
            if path and '/my/payment/link' in path:
                values.update({
                    'amount': sum(partner.payable_ids.mapped('amount'))
                })
            return values
        return {}

    @http.route(['/my/payment/create/partner'], type='json', auth='public', website=True)
    def page_system_payment_create_partner(self, **kwargs):
        message = self._check_create_partner(**kwargs)
        if message:
            return message

        values = {**kwargs}
        if 'tax_office' in values:
            values['paylox_tax_office'] = values['tax_office']
            del values['tax_office']
        keys = [value for value in values.keys()]

        company = request.env.company
        values.update({
            'company_id': company.id,
            'system': company.system,
        })
        if company.payment_advance_assign_salesperson and not request.env.user.share:
            values.update({
                'user_id': request.env.user.id,
            })
        try:
            if not values.get('vat'):
                raise UserError(_('Please enter ID number'))
            else:
                partner = request.env['res.partner'].sudo().search([
                    ('vat', '!=', False),
                    ('vat', '=', values['vat']),
                    ('company_id', '=', company.id)
                ], limit=1)
                if partner:
                    raise UserError(_('There is already a partner with the same ID Number'))

            if values.get('company_type') == 'company' and not values.get('paylox_tax_office'):
                raise UserError(_('Please enter a tax office'))

            if not values.get('email'):
                email = company.email
                if not email or '@' not in email:
                    email = 'vat@paylox.io'
                name, domain = email.rsplit('@', 1)
                values['email'] = '%s@%s' % (values['vat'], domain)

            partner = request.env['res.partner'].sudo().with_context(no_vat_validation=True).create(values)
            return partner.read(keys)[0] or {}
        except UserError as e:
            return {'error': str(e)}
        except Exception as e:
            raise Exception(e)

    @http.route(['/my/payment/share/link'], type='json', auth='public', website=True)
    def page_system_share_link(self, type, link, lang, value):
        return request.env['res.partner'].sudo().send_payment_link(type, link, lang, value)

    @http.route([
        '/p/<token>/report/<converter>/<reportname>',
        '/p/<token>/report/<converter>/<reportname>/<docids>',
    ], type='http', auth='public', website=True)
    def page_system_report_link(self, token, reportname, docids=None, converter=None, **data):
        if reportname not in REPORT_NAMES:
            raise MissingError(_('Report cannot be found'))

        partner = self._get_parent(token)
        if not partner:
            raise MissingError(_('Partner cannot be found'))

        user = request.env['res.users'].browse(SUPERUSER_ID)
        report = request.env['ir.actions.report'].sudo()._get_report_from_name(reportname)
        context = dict(request.env.context)

        if docids:
            docids = [int(i) for i in docids.split(',')]
        if data.get('options'):
            data.update(json.loads(data.pop('options')))
        if data.get('context'):
            data['context'] = json.loads(data['context'])
            context.update(data['context'])
        if converter == 'html':
            html = report.with_user(user).with_context(context).sudo()._render_qweb_html(docids, data=data)[0]
            return request.make_response(html)
        elif converter == 'pdf':
            pdf = report.with_context(context)._render_qweb_pdf(docids, data=data)[0]
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        elif converter == 'text':
            text = report.with_context(context)._render_qweb_text(docids, data=data)[0]
            texthttpheaders = [('Content-Type', 'text/plain'), ('Content-Length', len(text))]
            return request.make_response(text, headers=texthttpheaders)
        else:
            raise werkzeug.exceptions.HTTPException(description='Converter %s not implemented.' % converter)

    @http.route(['/paylox/payment/transactions/txt'], type='http', auth='user', methods=['GET'], sitemap=False, website=True)
    def page_transactions_txt(self, **data):
        result = []
        headers = [
            'UYEISYERINO',
            'TERMID',
            'ISLEMTARIHI',
            'GUNSONUTARIHI',
            'VALOR',
            'BATCHNO',
            'AUTHCODE',
            'PARABIRIMI',
            'ISLEMTIPI',
            'KARTNO',
            'KARTTIPI',
            'KARTKAYNAK',
            'TAKSITNO',
            'TAKSITSAYISI',
            'HAREKETTIPI',
            'TAKSITTUTARI',
            'ISLEMTUTARI',
            'KOMISYONTUTARI',
            'SERVISUCRETTUTARI',
            'KATKITUTARI',
            'KAMPANYAKATKITUTARI',
            'NETTUTAR',
            'MUSTERINO',
            ''
        ]
        result.append(';'.join(headers))

        txs = request.env['payment.transaction'].sudo().search([
            ('id', 'in', list(map(int, data[''].split(',')))),
            ('jetcheckout_payment_type', '=', 'virtual_pos'),
            ('company_id', '=', request.env.user.company_ids.ids),
            ('state', '=', 'done'),
        ])
        for tx in txs:
            values = [
                '000000000480150',
                'VP692034',
                tx.create_date.strftime('%d/%m/%Y'),
                tx.create_date.strftime('%d/%m/%Y'),
                tx.create_date.strftime('%d/%m/%Y'),
                '3120',
                '869286',
                'TL',
                'Peşin Satış - E-Ticaret',
                tx.jetcheckout_card_number,
                'KREDİ KART',
                'YURT İCİ',
                tx.jetcheckout_installment_count,
                tx.jetcheckout_installment_count,
                'A',
                '%0.2f' % tx.jetcheckout_installment_amount,
                '%0.2f' % tx.jetcheckout_payment_amount,
                '%0.2f' % tx.jetcheckout_customer_amount,
                '%0.2f' % tx.jetcheckout_commission_amount,
                '%0.2f' % tx.jetcheckout_fund_amount,
                '%0.2f' % 0,
                '%0.2f' % tx.jetcheckout_payment_net,
                tx.partner_id.ref,
                ''
            ]
            result.append(';'.join(map(str, values)))
        headers = [
            ('Content-Type', 'text/plain'),
            ('Content-Disposition', content_disposition('Transactions.txt'))
        ]
        return request.make_response('\n'.join(result), headers=headers)
