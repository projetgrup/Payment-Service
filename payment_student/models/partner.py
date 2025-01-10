# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.depends('child_ids.school_id')
    def _compute_schools(self):
        for partner in self:
            if partner.parent_id:
                partner.school_ids = False
            else:
                partner.school_ids = [(6, 0, partner.mapped('child_ids.school_id').ids)]

    system = fields.Selection(selection_add=[('student', 'Student Payment System')])
    school_id = fields.Many2one('res.student.school', ondelete='restrict')
    class_id = fields.Many2one('res.student.class', ondelete='restrict')
    bursary_id = fields.Many2one('res.student.bursary', ondelete='restrict')
    school_ids = fields.Many2many('res.student.school', string='Schools', compute='_compute_schools', store=True, readonly=True)

    system_student_campus_id = fields.Many2one('res.student.campus', string='Campus', ondelete='restrict')
    system_student_faculty_id = fields.Many2one('res.student.faculty', string='Faculty', ondelete='restrict')
    system_student_department_id = fields.Many2one('res.student.department', string='Department', ondelete='restrict')
    system_student_program_id = fields.Many2one('res.student.program', string='Program', ondelete='restrict')

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.company_id.system == 'student':
            if res.parent_id:
                templates = self.env['res.student.payment.template'].search([
                    ('school_id', '=', res.school_id.id),
                    '|', ('class_id', '=', res.class_id.id), ('class_id', '=', False),
                    ('company_id', '=', res.company_id.id),
                ])
                if templates:
                    val = []
                    term_id = self.env.context.get('term_id', False)
                    for template in templates:
                        val.append({
                            'child_id': res.id,
                            'parent_id': res.parent_id.id,
                            'term_id': term_id or template.term_id.id,
                            'payment_type_id': template.payment_type_id.id,
                            'amount': template.amount,
                            'campaign_id': res.parent_id.campaign_id.id,
                            'company_id': res.company_id.id,
                        })
                    self.env['payment.item'].sudo().create(val)
            else:
                campaign_id = self.env.context.get('campaign_id', False)
                if campaign_id:
                    res.write({'campaign_id': campaign_id})
        return res

    def _get_name(self):
        name = super()._get_name()
        system = self.env.context.get('active_system') or self.env.context.get('system')
        if not system == 'student':
            return name

        partner = self
        if self.env.context.get('show_address'):
            email = partner.email or _('No email')
            mobile = partner.mobile or _('No mobile')
            name = ' | '.join([name, email, mobile])
        return name

    def _get_payment_terms(self):
        self.ensure_one()
        payments = self.env['payment.item'].sudo().search([('parent_id','=',self.id),('paid','=',False)])
        if not payments:
            return ''
        return ', '.join(payments.mapped('term_id.name'))

    def _get_setting_line(self):
        self.ensure_one()
        line = self.company_id._get_student_discount_line()
        if line:
            month = line.date_start.strftime('%B')
            return {'month': month, 'installment': line.installment, 'percentage': line.percentage}
        return False

    @api.constrains('vat', 'email')
    def _check_student_vals(self):
        system = self.env.context.get('active_system') or self.env.context.get('system')
        if system == 'student' and self.env.user.has_group('payment_student.group_student_user') and not self.env.context.get('skip_student_vat_check'):
            for line in self:
                if line.vat and not line.is_company:
                    student = self.search([('id','!=',line.id),('vat','=',line.vat),('company_id','=',line.company_id.id)], limit=1)
                    if student:
                        raise UserError(_('There is already a student with the same Vat Number - %s') % student.name)
                elif line.email and line.is_company:
                    parent = self.search([('id','!=',line.id),('email','=',line.email),('company_id','=',line.company_id.id)], limit=1)
                    if parent:
                        raise UserError(_('There is already a parent with the same email - %s') % line.email)
