# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import frozendict
from odoo.exceptions import AccessDenied


class Users(models.Model):
    _inherit = 'res.users'

    def _compute_privilege(self):
        for user in self:
            system = user.company_id.system
            module = system or 'jetcheckout_system'
            name = system or 'system'
            if user.has_group('payment_%s.group_%s_manager' % (module, name)):
                user.privilege = 'admin'
            elif user.has_group('payment_%s.group_%s_user' % (module, name)):
                user.privilege = 'user'
            else:
                user.privilege = ''

    def _set_privilege(self):
        for user in self:
            system = user.company_id.system
            module = system or 'jetcheckout_system'
            name = system or 'system'
            group_system_user = self.env.ref('payment_jetcheckout_system.group_system_user')
            group_system_admin = self.env.ref('payment_jetcheckout_system.group_system_manager')
            group_user = self.env.ref('payment_%s.group_%s_user' % (module, name))
            group_admin = self.env.ref('payment_%s.group_%s_manager' % (module, name))
            group_public = self.env.ref('base.group_public')
            group_portal = self.env.ref('base.group_portal')
            group_internal = self.env.ref('base.group_user')

            try: # grant admin_tools groups if exists
                group_admin_show_delete = self.env.ref('admin_tools.group_show_delete')
                group_admin_show_export = self.env.ref('admin_tools.group_show_export')
                group_admin_show_duplicate = self.env.ref('admin_tools.group_show_duplicate')
                group_admin_show_create = self.env.ref('admin_tools.group_show_create')
                group_admin_show_edit = self.env.ref('admin_tools.group_show_edit')
                group_admin_show_print = self.env.ref('admin_tools.group_show_print')
                group_admin_show_action = self.env.ref('admin_tools.group_show_action')
            except:
                pass

            if user.has_group('base.group_public'):
                group_public.sudo().write({'users': [(3, user.id)]})
            if user.has_group('base.group_portal'):
                group_portal.sudo().write({'users': [(3, user.id)]})
            if not user.has_group('base.group_user'):
                group_internal.sudo().write({'users': [(4, user.id)]})

            if user.privilege == 'admin':
                group_admin.sudo().write({'users': [(4, user.id)]})
                group_user.sudo().write({'users': [(4, user.id)]})
                group_system_admin.sudo().write({'users': [(4, user.id)]})
                group_system_user.sudo().write({'users': [(4, user.id)]})

                try:
                    group_admin_show_delete.sudo().write({'users': [(4, user.id)]})
                    group_admin_show_export.sudo().write({'users': [(4, user.id)]})
                    group_admin_show_duplicate.sudo().write({'users': [(4, user.id)]})
                    group_admin_show_create.sudo().write({'users': [(4, user.id)]})
                    group_admin_show_edit.sudo().write({'users': [(4, user.id)]})
                    group_admin_show_print.sudo().write({'users': [(4, user.id)]})
                    group_admin_show_action.sudo().write({'users': [(4, user.id)]})
                except:
                    pass

            elif user.privilege == 'user':
                group_admin.sudo().write({'users': [(3, user.id)]})
                group_user.sudo().write({'users': [(4, user.id)]})
                group_system_admin.sudo().write({'users': [(3, user.id)]})
                group_system_user.sudo().write({'users': [(4, user.id)]})

                try:
                    group_admin_show_delete.sudo().write({'users': [(3, user.id)]})
                    group_admin_show_export.sudo().write({'users': [(4, user.id)]})
                    group_admin_show_duplicate.sudo().write({'users': [(4, user.id)]})
                    group_admin_show_create.sudo().write({'users': [(4, user.id)]})
                    group_admin_show_edit.sudo().write({'users': [(4, user.id)]})
                    group_admin_show_print.sudo().write({'users': [(4, user.id)]})
                    group_admin_show_action.sudo().write({'users': [(4, user.id)]})
                except:
                    pass

            else:
                group_user.sudo().write({'users': [(3, user.id)]})
                group_admin.sudo().write({'users': [(3, user.id)]})
                group_system_admin.sudo().write({'users': [(3, user.id)]})
                group_system_user.sudo().write({'users': [(3, user.id)]})

                try:
                    group_admin_show_delete.sudo().write({'users': [(3, user.id)]})
                    group_admin_show_export.sudo().write({'users': [(3, user.id)]})
                    group_admin_show_duplicate.sudo().write({'users': [(3, user.id)]})
                    group_admin_show_create.sudo().write({'users': [(3, user.id)]})
                    group_admin_show_edit.sudo().write({'users': [(3, user.id)]})
                    group_admin_show_print.sudo().write({'users': [(3, user.id)]})
                    group_admin_show_action.sudo().write({'users': [(3, user.id)]})
                except:
                    pass

    def _compute_group_transaction_commission(self):
        for user in self:
            user.group_transaction_commission = user.has_group('payment_jetcheckout.group_transaction_commission')

    def _set_group_transaction_commission(self):
        for user in self:
            code = user.group_transaction_commission and 4 or 3
            group = self.env.ref('payment_jetcheckout.group_transaction_commission')
            group.sudo().write({'users': [(code, user.id)]})

    def _compute_group_transaction_cancel(self):
        for user in self:
            user.group_transaction_cancel = user.has_group('payment_jetcheckout.group_transaction_cancel')

    def _set_group_transaction_cancel(self):
        for user in self:
            code = user.group_transaction_cancel and 4 or 3
            group = self.env.ref('payment_jetcheckout.group_transaction_cancel')
            group.sudo().write({'users': [(code, user.id)]})
 
    def _compute_group_transaction_refund(self):
        for user in self:
            user.group_transaction_refund = user.has_group('payment_jetcheckout.group_transaction_refund')

    def _set_group_transaction_refund(self):
        for user in self:
            code = user.group_transaction_refund and 4 or 3
            group = self.env.ref('payment_jetcheckout.group_transaction_refund')
            group.sudo().write({'users': [(code, user.id)]})

    def _compute_group_own_partner(self):
        for user in self:
            user.group_own_partner = user.has_group('payment_jetcheckout_system.group_system_own_partner')

    def _set_group_own_partner(self):
        for user in self:
            code = user.group_own_partner and 4 or 3
            group = self.env.ref('payment_jetcheckout_system.group_system_own_partner')
            group.sudo().write({'users': [(code, user.id)]})

    def _compute_group_own_transaction(self):
        for user in self:
            user.group_own_transaction = user.has_group('payment_jetcheckout_system.group_system_own_transaction')

    def _set_group_own_transaction(self):
        for user in self:
            code = user.group_own_transaction and 4 or 3
            group = self.env.ref('payment_jetcheckout_system.group_system_own_transaction')
            group.sudo().write({'users': [(code, user.id)]})

    def _compute_group_create_partner(self):
        for user in self:
            user.group_create_partner = user.has_group('payment_jetcheckout_system.group_system_create_partner')

    def _set_group_create_partner(self):
        for user in self:
            code = user.group_create_partner and 4 or 3
            group = self.env.ref('payment_jetcheckout_system.group_system_create_partner')
            group.sudo().write({'users': [(code, user.id)]})

    def _compute_group_grant_partner(self):
        for user in self:
            user.group_grant_partner = user.has_group('payment_jetcheckout_system.group_system_grant_partner')

    def _set_group_grant_partner(self):
        for user in self:
            code = user.group_grant_partner and 4 or 3
            group = self.env.ref('payment_jetcheckout_system.group_system_grant_partner')
            group.sudo().write({'users': [(code, user.id)]})

    def _compute_group_show_payment_link(self):
        for user in self:
            user.group_show_payment_link = user.has_group('payment_jetcheckout_system.group_show_payment_link')

    def _set_group_show_payment_link(self):
        for user in self:
            code = user.group_show_payment_link and 4 or 3
            group = self.env.ref('payment_jetcheckout_system.group_show_payment_link')
            group.sudo().write({'users': [(code, user.id)]})

    def _compute_group_show_campaign_button(self):
        for user in self:
            user.group_show_campaign_button = user.has_group('payment_jetcheckout_system.group_show_campaign_button')

    def _set_group_show_campaign_button(self):
        for user in self:
            code = user.group_show_campaign_button and 4 or 3
            group = self.env.ref('payment_jetcheckout_system.group_show_campaign_button')
            group.sudo().write({'users': [(code, user.id)]})

    def _compute_payment_page_item_priority(self):
        for user in self:
            user.payment_page_item_priority_selection = user.payment_page_item_priority and 'ok' or 'no'

    def _set_payment_page_item_priority(self):
        for user in self:
            user.payment_page_item_priority = user.payment_page_item_priority_selection == 'ok'

    privilege = fields.Selection([('user','User'),('admin','Administrator')], string='Privilege Type', compute='_compute_privilege', inverse='_set_privilege')
    group_transaction_commission = fields.Boolean(string='Transaction Commissions', compute='_compute_group_transaction_commission', inverse='_set_group_transaction_commission')
    group_transaction_cancel = fields.Boolean(string='Transaction Cancel', compute='_compute_group_transaction_cancel', inverse='_set_group_transaction_cancel')
    group_transaction_refund = fields.Boolean(string='Transaction Refund', compute='_compute_group_transaction_refund', inverse='_set_group_transaction_refund')
    group_own_partner = fields.Boolean(string='Only Own Partners', compute='_compute_group_own_partner', inverse='_set_group_own_partner')
    group_own_transaction = fields.Boolean(string='Only Own Transactions', compute='_compute_group_own_transaction', inverse='_set_group_own_transaction')
    group_create_partner = fields.Boolean(string='Create Partners', compute='_compute_group_create_partner', inverse='_set_group_create_partner')
    group_grant_partner = fields.Boolean(string='Grant Partners', compute='_compute_group_grant_partner', inverse='_set_group_grant_partner')
    group_show_payment_link = fields.Boolean(string='Show Payment Link', compute='_compute_group_show_payment_link', inverse='_set_group_show_payment_link')
    group_show_campaign_button = fields.Boolean(string='Show Campaign Button', compute='_compute_group_show_campaign_button', inverse='_set_group_show_campaign_button')

    payment_page_ok = fields.Boolean(string='Payment Page Active', default=True)
    payment_contactless_ok = fields.Boolean(string='Contactless Payment Page Active')
    payment_preview_ok = fields.Boolean(string='Payment Preview Page Active', default=True)
    payment_page_item_priority = fields.Boolean(string='Payment Page Items Priority')
    payment_page_item_priority_selection = fields.Selection([
        ('no', 'All items can be selected'),
        ('ok', 'Items can be selected respectively'),
    ], string='Payment Page Items Priority Selection', compute='_compute_payment_page_item_priority', inverse='_set_payment_page_item_priority')

    def _check_token(self, token):
        pid, token = self.partner_id._resolve_token(token)
        if not self.partner_id.id == pid or not self.partner_id.access_token == token:
            raise AccessDenied()

    def _check_credentials(self, password, env):
        env = env or {}
        if env.get('token', False):
            return self._check_token(env['token'])
        return super()._check_credentials(password, env)

    @classmethod
    def authenticate(cls, db, login, password, env):
        if isinstance(password, dict):
            env = env or {}
            if 'company' in password:
                env['company'] = password['company']
            if 'token' in password:
                env['token'] = password['token']
                password = password['token']
        return super(Users, cls).authenticate(db, login, password, env)

    @api.model
    def default_get(self, fields):
        values = super(Users, self).default_get(fields)
        system = self.env.company.system
        if system:
            template = self.sudo().search([('login', '=', system), ('active', '=', False)], limit=1)
            if template:
                values['notification_type'] = template.notification_type
                values['action_id'] = template.action_id
                values['lang'] = template.lang
                values['tz'] = template.tz
        return values

    @api.model
    def create(self, values):
        if not self.env.user.has_group('base.group_erp_manager') and self.env.user.has_group('payment_jetcheckout_system.group_system_user'):
            self = self.sudo()

        res = super(Users, self.with_context(mail_channel_nosubscribe=True)).create(values)
        res.company_id._update_subsystem()
        return res

    def write(self, values):
        if not self.env.user.has_group('base.group_erp_manager') and self.env.user.has_group('payment_jetcheckout_system.group_system_user'):
            self = self.sudo()

        res = super(Users, self).write(values)
        for user in self:
            if 'company_id' in values:
                user.company_id._update_subsystem()
                user.partner_id.company_id = user.company_id.system and user.company_id.id or False
        return res

    def context_get(self):
        ctx = super(Users, self).context_get()
        context = dict(ctx)
        context['system'] = self.env.context.get('system')
        context['subsystem'] = self.env.context.get('subsystem')
        return frozendict(context)

    def action_reset_password(self):
        if self.company_id.system:
            return super(Users, self.sudo()).action_reset_password()
        return super(Users, self).action_reset_password()
    
    def action_set_password(self):
        return self.env.ref('base.change_password_wizard_action').sudo().read()[0]
