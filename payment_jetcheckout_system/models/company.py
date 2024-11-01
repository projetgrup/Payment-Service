# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Company(models.Model):
    _inherit = 'res.company'

    def _compute_is_admin(self):
        for company in self:
            company.is_admin = self.env.user.has_group('base.group_system')

    def _compute_mail_server(self):
        for company in self:
            company.mail_server_id = self.env['ir.mail_server'].search([('company_id', '=', company.id)], limit=1).id

    tax_office = fields.Char()
    system = fields.Selection([])
    subsystem = fields.Selection([])
    required_2fa = fields.Boolean('Two Factor Required')
    is_admin = fields.Boolean(compute='_compute_is_admin', compute_sudo=True)
    mail_server_id = fields.Many2one('ir.mail_server', compute='_compute_mail_server', compute_sudo=True)

    notif_mail_success_ok = fields.Boolean('Send Successful Payment Transaction Email')
    notif_sms_success_ok = fields.Boolean('Send Successful Payment Transaction SMS')
    notif_webhook_ids = fields.One2many('payment.settings.notification.webhook', 'company_id', 'Webhook URLs')

    payment_dashboard_button_ok = fields.Boolean(string='Dashboard Payment Button', default=True)
    payment_dashboard_button_url = fields.Char(string='Dashboard Payment Button URL')
    payment_dashboard_button_contactless_ok = fields.Boolean(string='Dashboard Contactless Payment Button', default=True)
    payment_dashboard_button_contactless_url = fields.Char(string='Dashboard Contactless Payment Button URL')
    payment_dashboard_field_amount = fields.Selection([
        ('jetcheckout_payment_paid', 'Paid Amount'),
        ('jetcheckout_payment_amount', 'Payable Amount'),
        ('jetcheckout_payment_net', 'Net Amount'),
        ('jetcheckout_fund_amount', 'Fund Amount'),
    ], string='Dashboard Payment Amount Field', default='jetcheckout_payment_paid')

    payment_transaction_export_txt = fields.Boolean(string='Payment Trasansaction Export TXT')

    payment_page_advance_ok = fields.Boolean(string='Payment Page Advance')
    payment_page_due_ok = fields.Boolean(string='Payment Page Due')
    payment_page_due_ids = fields.One2many('payment.settings.due', 'company_id', 'Payment Page Dues')
    payment_page_due_base = fields.Selection([
        ('date_due', 'Due Date'),
        ('date_document', 'Document Date'),
    ], string='Payment Page Due Base Date', default='date_due')
    payment_page_due_hide_payment_ok = fields.Boolean(string='Payment Page Due Hide Payment Form')
    payment_page_due_hide_payment_message = fields.Text(string='Payment Page Due Hide Payment Message', translate=True)

    payment_page_due_reminder_ok = fields.Boolean(string='Payment Page Due Reminder')
    payment_page_due_reminder_day = fields.Integer(string='Payment Page Due Reminder Day')
    payment_page_due_reminder_user_ids = fields.Many2many('res.users', string='Payment Page Due Reminder Sales Representatives')
    payment_page_due_reminder_user_ok = fields.Boolean(string='Payment Page Due Reminder Sales Representative Included')
    payment_page_due_reminder_team_ids = fields.Many2many('crm.team', string='Payment Page Due Reminder Sales Teams')
    payment_page_due_reminder_team_ok = fields.Boolean(string='Payment Page Due Reminder Sales Teams Included')
    payment_page_due_reminder_partner_ids = fields.Many2many('res.partner', string='Payment Page Due Reminder Partners')
    payment_page_due_reminder_partner_ok = fields.Boolean(string='Payment Page Due Reminder Partners Included')
    payment_page_due_reminder_tag_ids = fields.Many2many('res.partner.category', string='Payment Page Due Reminder Partner Tags')
    payment_page_due_reminder_tag_ok = fields.Boolean(string='Payment Page Due Reminder Partner Tags Included')

    payment_page_campaign_tag_ids = fields.One2many('payment.settings.campaign.tag', 'company_id', 'Payment Page Campaign Tags')
    payment_page_amount_editable = fields.Boolean(string='Payment Page Editable Amount')
    payment_page_item_priority = fields.Boolean(string='Payment Page Items Priority')
    payment_page_button_access_transaction = fields.Boolean(string='Payment Page See All Transactions')
    payment_page_flow = fields.Selection([
        ('static', 'Static'),
        ('dynamic', 'Dynamic'),
    ], string='Payment Page Flow', default='static')
    payment_page_ok = fields.Boolean(string='Payment Page Active', default=True)

    payment_advance_assign_salesperson = fields.Boolean(string='Payment Advance Assign Salesperson')
    payment_advance_amount_readonly = fields.Boolean(string='Payment Advance Amount Readonly')
    payment_advance_ok = fields.Boolean(string='Payment Advance Active')

    @api.model
    def create(self, vals):
        company = super(Company, self.with_context(skip_company=True)).create(vals)
        if 'system' in vals:
            company.partner_id.write({
                'company_id': company.id,
                'system': vals['system'],
            })
        return company

    def write(self, vals):
        if 'system' in vals:
            if self.env.user.has_group('base.group_system'):
                for company in self:
                    company.partner_id.write({
                        'company_id': company.id,
                        'system': vals['system'],
                    })
            else:
                del vals['system']

        res = super().write(vals)
        if 'subsystem' in vals:
            self._update_subsystem()
        return res

    @api.onchange('system')
    def onchange_system(self):
        self.subsystem = False

    def _update_subsystem(self, users=None):
        for company in self:
            values = []
            if company.system:
                if company.subsystem:
                    system = company.system
                    subsystem = company.subsystem.replace('%s_' % system, '')
                    active_ids = self.env['ir.model.data'].sudo().search_read([
                        ('model', '=', 'res.groups'),
                        ('module', '=', 'payment_%s' % system),
                        ('name', '=', 'group_subsystem_%s' % subsystem)
                    ], ['res_id'], limit=1)
                    values.extend([(4, active_id['res_id']) for active_id in active_ids])

                    inactive_ids = self.env['ir.model.data'].sudo().search_read([
                        ('model', '=', 'res.groups'),
                        ('module', '=', 'payment_%s' % system),
                        ('name', 'like', 'group_subsystem_%'),
                        ('name', '!=', 'group_subsystem_%s' % subsystem),
                    ], ['res_id'])
                    values.extend([(3, inactive_id['res_id']) for inactive_id in inactive_ids])

                else:
                    inactive_ids = self.env['ir.model.data'].sudo().search_read([
                        ('model', '=', 'res.groups'),
                        ('module', '=', 'payment_%s' % company.system),
                        ('name', 'like', 'group_subsystem_%')
                    ], ['res_id'])
                    values.extend([(3, inactive_id['res_id']) for inactive_id in inactive_ids])
            else:
                inactive_ids = self.env['ir.model.data'].sudo().search_read([
                    ('model', '=', 'res.groups'),
                    ('module', 'like', 'payment_%'),
                    ('name', 'like', 'group_subsystem_%')
                ], ['res_id'])
                values.extend([(3, inactive_id['res_id']) for inactive_id in inactive_ids])

            if values:
                if not users:
                    users = self.env['res.users'].sudo().with_context(active_test=False).search([
                        ('share', '=', False),
                        ('company_id', '=', company.id),
                    ])
                users.write({'groups_id': values})
