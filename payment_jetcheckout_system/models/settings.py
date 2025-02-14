# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError


class PaymentSettings(models.TransientModel):
    _name = 'payment.settings'
    _description = 'Payment Settings'

    @api.constrains('payment_page_campaign_tag_ids')
    def _check_payment_page_campaign_tag_ids(self):
        for setting in self:
            tags = setting.payment_page_campaign_tag_ids
            if tags:
                tags = tags.filtered(lambda x: not x.campaign_id)
                if not len(tags) == 1:
                    raise UserError(_('There must only one campaign tag without campaign selection'))

    @api.depends('company_id')
    def _compute_payment_page_campaign_table_opt(self):
        for setting in self:
            setting.payment_page_campaign_table_opt = 'include' if setting.company_id.payment_page_campaign_table_included else 'exclude'

    @api.depends('company_id')
    def _compute_payment_page_due_reminder_user_opt(self):
        for setting in self:
            setting.payment_page_due_reminder_user_opt = 'include' if setting.company_id.payment_page_due_reminder_user_ok else 'exclude'

    @api.depends('company_id')
    def _compute_payment_page_due_reminder_team_opt(self):
        for setting in self:
            setting.payment_page_due_reminder_team_opt = 'include' if setting.company_id.payment_page_due_reminder_team_ok else 'exclude'

    @api.depends('company_id')
    def _compute_payment_page_due_reminder_partner_opt(self):
        for setting in self:
            setting.payment_page_due_reminder_partner_opt = 'include' if setting.company_id.payment_page_due_reminder_partner_ok else 'exclude'

    @api.depends('company_id')
    def _compute_payment_page_due_reminder_tag_opt(self):
        for setting in self:
            setting.payment_page_due_reminder_tag_opt = 'include' if setting.company_id.payment_page_due_reminder_tag_ok else 'exclude'

    def _set_payment_page_campaign_table_opt(self):
        for setting in self:
            setting.company_id.payment_page_campaign_table_included = setting.payment_page_campaign_table_opt == 'include'

    def _set_payment_page_due_reminder_user_opt(self):
        for setting in self:
            setting.company_id.payment_page_due_reminder_user_ok = setting.payment_page_due_reminder_user_opt == 'include'

    def _set_payment_page_due_reminder_team_opt(self):
        for setting in self:
            setting.company_id.payment_page_due_reminder_team_ok = setting.payment_page_due_reminder_team_opt == 'include'

    def _set_payment_page_due_reminder_partner_opt(self):
        for setting in self:
            setting.company_id.payment_page_due_reminder_partner_ok = setting.payment_page_due_reminder_partner_opt == 'include'

    def _set_payment_page_due_reminder_tag_opt(self):
        for setting in self:
            setting.company_id.payment_page_due_reminder_tag_ok = setting.payment_page_due_reminder_tag_opt == 'include'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    required_2fa = fields.Boolean(related='company_id.required_2fa', readonly=False)

    payment_item_bank_token_ok = fields.Boolean(related='company_id.payment_item_bank_token_ok', readonly=False)
    payment_dashboard_button_ok = fields.Boolean(related='company_id.payment_dashboard_button_ok', readonly=False)
    payment_dashboard_button_url = fields.Char(related='company_id.payment_dashboard_button_url', readonly=False)
    payment_dashboard_button_contactless_ok = fields.Boolean(related='company_id.payment_dashboard_button_contactless_ok', readonly=False)
    payment_dashboard_button_contactless_url = fields.Char(related='company_id.payment_dashboard_button_contactless_url', readonly=False)
    payment_dashboard_field_amount = fields.Selection(related='company_id.payment_dashboard_field_amount', readonly=False)

    payment_transaction_export_txt = fields.Boolean(related='company_id.payment_transaction_export_txt', readonly=False)

    payment_advance_amount_readonly = fields.Boolean(related='company_id.payment_advance_amount_readonly', readonly=False)
    payment_advance_ok = fields.Boolean(related='company_id.payment_advance_ok', readonly=False)
    payment_token_ok = fields.Boolean(related='company_id.payment_token_ok', readonly=False)
    payment_point_ok = fields.Boolean(related='company_id.payment_point_ok', readonly=False)

    payment_page_ok = fields.Boolean(related='company_id.payment_page_ok', readonly=False)
    payment_page_flow = fields.Selection(related='company_id.payment_page_flow', readonly=False)
    payment_page_description_ok = fields.Boolean(related='company_id.payment_page_description_ok', readonly=False)
    payment_page_amount_editable = fields.Boolean(related='company_id.payment_page_amount_editable', readonly=False)
    payment_page_saleref_ok = fields.Boolean(related='company_id.payment_page_saleref_ok', readonly=False)
    payment_page_item_priority = fields.Boolean(related='company_id.payment_page_item_priority', readonly=False)
    payment_page_item_add_ok = fields.Boolean(related='company_id.payment_page_item_add_ok', readonly=False)
    payment_page_item_expire_ok = fields.Boolean(related='company_id.payment_page_item_expire_ok', readonly=False)
    payment_page_item_expire_value = fields.Integer(related='company_id.payment_page_item_expire_value', readonly=False)
    payment_page_item_expire_period = fields.Selection(related='company_id.payment_page_item_expire_period', readonly=False)
    payment_page_item_add_date_readonly = fields.Boolean(related='company_id.payment_page_item_add_date_readonly', readonly=False)
    payment_page_item_add_desc_prefix = fields.Char(related='company_id.payment_page_item_add_desc_prefix', readonly=False)
    payment_page_item_add_desc_maxlength = fields.Integer(related='company_id.payment_page_item_add_desc_maxlength', readonly=False)
    payment_page_token_wo_commission = fields.Boolean(related='company_id.payment_page_token_wo_commission', readonly=False)

    payment_page_campaign_tag_ids = fields.One2many(related='company_id.payment_page_campaign_tag_ids', readonly=False)
    payment_page_campaign_table_ok = fields.Boolean(related='company_id.payment_page_campaign_table_ok', readonly=False)
    payment_page_campaign_table_transpose = fields.Boolean(related='company_id.payment_page_campaign_table_transpose', readonly=False)
    payment_page_campaign_table_ids = fields.Many2many(related='company_id.payment_page_campaign_table_ids', readonly=False)
    payment_page_campaign_table_included = fields.Boolean(related='company_id.payment_page_campaign_table_included', readonly=False)
    payment_page_campaign_table_opt = fields.Selection([('include', 'include'), ('exclude', 'exclude')], compute='_compute_payment_page_campaign_table_opt', inverse='_set_payment_page_campaign_table_opt', string='Campaigns on Campaign Table Included on Payment Page Option')

    payment_page_advance_ok = fields.Boolean(related='company_id.payment_page_advance_ok', readonly=False)
    payment_advance_assign_salesperson = fields.Boolean(related='company_id.payment_advance_assign_salesperson', readonly=False)
    payment_page_button_access_transaction = fields.Boolean(related='company_id.payment_page_button_access_transaction', readonly=False)
    payment_page_due_ok = fields.Boolean(related='company_id.payment_page_due_ok', readonly=False)
    payment_page_due_ids = fields.One2many(related='company_id.payment_page_due_ids', readonly=False)
    payment_page_due_base = fields.Selection(related='company_id.payment_page_due_base', readonly=False)
    payment_page_due_hide_payment_ok = fields.Boolean(related='company_id.payment_page_due_hide_payment_ok', readonly=False)
    payment_page_due_hide_payment_message = fields.Text(related='company_id.payment_page_due_hide_payment_message', readonly=False)

    payment_page_due_reminder_ok = fields.Boolean(related='company_id.payment_page_due_reminder_ok', readonly=False)
    payment_page_due_reminder_day = fields.Integer(related='company_id.payment_page_due_reminder_day', readonly=False)
    payment_page_due_reminder_user_ids = fields.Many2many(related='company_id.payment_page_due_reminder_user_ids', readonly=False)
    payment_page_due_reminder_user_ok = fields.Boolean(related='company_id.payment_page_due_reminder_user_ok', readonly=False)
    payment_page_due_reminder_user_opt = fields.Selection([('include', 'include'), ('exclude', 'exclude')], compute='_compute_payment_page_due_reminder_user_opt', inverse='_set_payment_page_due_reminder_user_opt', string='Payment Page Due Reminder Sales Representative Option')
    payment_page_due_reminder_team_ids = fields.Many2many(related='company_id.payment_page_due_reminder_team_ids', readonly=False)
    payment_page_due_reminder_team_ok = fields.Boolean(related='company_id.payment_page_due_reminder_team_ok', readonly=False)
    payment_page_due_reminder_team_opt = fields.Selection([('include', 'include'), ('exclude', 'exclude')], compute='_compute_payment_page_due_reminder_team_opt', inverse='_set_payment_page_due_reminder_team_opt', string='Payment Page Due Reminder Sales Teams Option')
    payment_page_due_reminder_partner_ids = fields.Many2many(related='company_id.payment_page_due_reminder_partner_ids', readonly=False)
    payment_page_due_reminder_partner_ok = fields.Boolean(related='company_id.payment_page_due_reminder_partner_ok', readonly=False)
    payment_page_due_reminder_partner_opt = fields.Selection([('include', 'include'), ('exclude', 'exclude')], compute='_compute_payment_page_due_reminder_partner_opt', inverse='_set_payment_page_due_reminder_partner_opt', string='Payment Page Due Reminder Partners Option')
    payment_page_due_reminder_tag_ids = fields.Many2many(related='company_id.payment_page_due_reminder_tag_ids', readonly=False)
    payment_page_due_reminder_tag_ok = fields.Boolean(related='company_id.payment_page_due_reminder_tag_ok', readonly=False)
    payment_page_due_reminder_tag_opt = fields.Selection([('include', 'include'), ('exclude', 'exclude')], compute='_compute_payment_page_due_reminder_tag_opt', inverse='_set_payment_page_due_reminder_tag_opt', string='Payment Page Due Reminder Partner Tags Option')

    notif_mail_success_ok = fields.Boolean(related='company_id.notif_mail_success_ok', readonly=False)
    notif_sms_success_ok = fields.Boolean(related='company_id.notif_sms_success_ok', readonly=False)
    notif_webhook_ids = fields.One2many(related='company_id.notif_webhook_ids', readonly=False)

    def start(self):
        return self.next()

    def copy(self, values):
        raise UserError(_('Cannot duplicate configuration!'), '')

    def next(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def execute(self):
        return self.next()

    def cancel(self):
        return self.refresh()

    def refresh(self):
        actions = self.env['ir.actions.act_window'].sudo().search([('res_model', '=', self._name)], limit=1)
        if actions:
            return actions.read()[0]
        return {}

    def name_get(self):
        action = self.env['ir.actions.act_window'].sudo().search([('res_model', '=', self._name)], limit=1)
        name = action.name or self._name
        return [(record.id, name) for record in self]

    @api.model
    def create(self, values):
        for field in self._fields.values():
            if not (field.name in values and field.related and not field.readonly):
                continue

            fname0, *fnames = field.related.split(".")
            if fname0 not in values:
                continue

            field0 = self._fields[fname0]
            old_value = field0.convert_to_record(field0.convert_to_cache(values[fname0], self), self)

            for fname in fnames:
                old_value = next(iter(old_value), old_value)[fname]

            new_value = field.convert_to_record(field.convert_to_cache(values[field.name], self), self)

            if old_value == new_value:
                values.pop(field.name)

        return super(PaymentSettings, self).create(values)


class PaymentSettingsNotificationWebhook(models.Model):
    _name = 'payment.settings.notification.webhook'
    _description = 'Payment Settings Notification Webhook'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    url = fields.Char('URL', required=True)

class PaymentSettingsDue(models.Model):
    _name = 'payment.settings.due'
    _description = 'Payment Settings Dues'
    _order = 'due'

    @api.model
    def _get_acquirers(self, partner=None, limit=None):
        company = partner and partner.company_id or self.env.company
        return self.env['payment.acquirer'].sudo()._get_acquirer(company=company, providers=['jetcheckout'], limit=limit, raise_exception=False)

    @api.onchange('due')
    def _compute_unit(self):
        for line in self:
            if line.due > 1:
                line.unit = _('Days')
            else:
                line.unit = _('Day')

    @api.onchange('due')
    def _compute_campaign_ids(self):
        for line in self:
            acquirers = self._get_acquirers()
            campaigns = acquirers.mapped('paylox_campaign_ids')
            line.campaign_ids = [(6, 0, campaigns.ids)]

    def _default_campaign_id(self):
        acquirers = self._get_acquirers(limit=1)
        if acquirers:
            return acquirers.jetcheckout_campaign_id.id
        return False

    due = fields.Integer('Due', default=0, required=True)
    tolerance = fields.Integer('Tolerance', default=0, required=True)
    unit = fields.Char('Unit', compute='_compute_unit')
    round = fields.Boolean('Round')
    mail_template_id = fields.Many2one('mail.template', string='Email Template')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    campaign_id = fields.Many2one('payment.acquirer.jetcheckout.campaign', string='Campaign', ondelete='set null', domain='[("id", "in", campaign_ids)]', default=_default_campaign_id)
    campaign_ids = fields.Many2many('payment.acquirer.jetcheckout.campaign', 'Campaigns', compute='_compute_campaign_ids')
    partner_tag_ids = fields.Many2many('res.partner.category', 'payment_settings_due_partner_tag_rel', 'due_id', 'tag_id', string='Tags')

    def get_campaign(self, partner, day):
        advance = None
        for due in self:
            if due.partner_tag_ids and due.partner_tag_ids.ids not in partner.category_id.ids:
                continue
            rounding_method = 'HALF-UP' if due.round else 'DOWN'
            days = float_round(day, precision_digits=0, rounding_method=rounding_method)
            if due.due + due.tolerance >= days:
                return int(days), due.campaign_id.name or '', due, advance, False
            advance = due

        days = float_round(day, precision_digits=0)
        return int(days), '', advance, advance, self.env.company.payment_page_due_hide_payment_ok


class PaymentSettingsDueTag(models.Model):
    _name = 'payment.settings.due.tag'
    _description = 'Payment Settings Due Tags'

    due_id = fields.Many2one('payment.settings.due')
    name = fields.Char(required=True)


class PaymentSettingsCampaignTag(models.Model):
    _name = 'payment.settings.campaign.tag'
    _description = 'Payment Settings Campaign Tags'
    _order = 'sequence, id'

    @api.model
    def _get_acquirers(self, partner=None, limit=None):
        company = partner and partner.company_id or self.env.company
        return self.env['payment.acquirer'].sudo()._get_acquirer(company=company, providers=['jetcheckout'], limit=limit, raise_exception=False)

    @api.onchange('name')
    def _compute_campaign_ids(self):
        for line in self:
            acquirers = self._get_acquirers()
            campaigns = acquirers.mapped('paylox_campaign_ids')
            line.campaign_ids = [(6, 0, campaigns.ids)]

    def _default_campaign_id(self):
        acquirers = self._get_acquirers(limit=1)
        if acquirers:
            return acquirers.jetcheckout_campaign_id.id
        return False

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Tag', required=True)
    campaign_id = fields.Many2one('payment.acquirer.jetcheckout.campaign', string='Campaign', ondelete='cascade', domain='[("id", "in", campaign_ids)]', default=_default_campaign_id)
    campaign_ids = fields.Many2many('payment.acquirer.jetcheckout.campaign', 'Campaigns', compute='_compute_campaign_ids')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    line_ids = fields.One2many('payment.settings.campaign.tag.line', 'campaign_id', 'Tags')

    def action_show_lines(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'name': self.name,
            'view_mode': 'form',
            'target': 'new',
            'context': {'dialog_size': 'small'}
        }

        '''return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.settings.campaign.tag.line',
            'name': self.name,
            'view_mode': 'tree',
            'target': 'new',
            'domain': [('campaign_id', '=', self.id)],
            'context': {
                'default_campaign_id': self.id,
                'dialog_size': 'small',
                'no_breadcrumbs': True
            }
        }'''

    def confirm(self):
        return


class PaymentSettingsCampaignTagLine(models.Model):
    _name = 'payment.settings.campaign.tag.line'
    _description = 'Payment Settings Campaign Tag Lines'

    campaign_id = fields.Many2one('payment.settings.campaign.tag')
    name = fields.Char(required=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.depends('company_id')
    def _compute_payment_page_ids(self):
        pages = self.env['payment.page'].search([])
        for setting in self:
            setting.payment_page_ids = pages

    payment_default_email_setting = fields.Boolean(string='Payment Default Email Settings', config_parameter='paylox.email.default')
    payment_default_email_server = fields.Many2one('ir.mail_server', string='Payment Default Email Server', config_parameter='paylox.email.server')
    payment_default_email_template = fields.Many2one('mail.template', string='Payment Default Email Template', config_parameter='paylox.email.template')
    payment_default_sms_setting = fields.Boolean(string='Payment Default SMS Settings', config_parameter='paylox.sms.default')
    payment_default_sms_provider = fields.Many2one('sms.provider', string='Payment Default SMS Provider', config_parameter='paylox.sms.provider')
    payment_default_sms_template = fields.Many2one('sms.template', string='Payment Default SMS Settings', config_parameter='paylox.sms.template')

    payment_page_ids = fields.One2many('payment.page', string='Payment Pages', compute='_compute_payment_page_ids', compute_sudo=True)
