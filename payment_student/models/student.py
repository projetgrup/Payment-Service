# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StudentPaymentTable(models.TransientModel):
    _name = 'res.student.payment.table'
    _description = 'Payment Table'

    table = fields.Html(string='Payment Table', sanitize=False, readonly=True)


class StudentDiscount(models.Model):
    _name = 'res.student.discount'
    _description = 'Payment Discounts'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', ondelete='cascade')
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    installment = fields.Integer(string='Installment')
    percentage = fields.Float(string='Discount (%)')

    @api.model
    def create(self, vals):
        if 'date_start' in vals and 'date_end' in vals and vals['date_start'] > vals['date_end']:
            raise UserError(_('Start date cannot be higher than end date'))
        if 'percentage' in vals and vals['percentage'] <= 0:
            raise UserError(_('Discount percentage must be higher than zero'))
        if 'installment' in vals and vals['installment'] <= 0:
            raise UserError(_('Installment must be higher than zero'))
        return super().create(vals)

    def write(self, vals):
        if 'date_start' in vals and 'date_end' in vals and vals['date_start'] > vals['date_end']:
            raise UserError(_('Start date cannot be higher than end date'))
        if 'percentage' in vals and vals['percentage'] <= 0:
            raise UserError(_('Discount percentage must be higher than zero'))
        if 'installment' in vals and vals['installment'] <= 0:
            raise UserError(_('Installment must be higher than zero'))
        return super().write(vals)


class StudentSchool(models.Model):
    _name = 'res.student.school'
    _description = 'Schools'
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    code = fields.Char()
    res_id = fields.Integer()
    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', default=lambda self: self.env.company, domain=[('system','=','student')])


class StudentCampus(models.Model):
    _name = 'res.student.campus'
    _description = 'Campuses'
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    code = fields.Char()
    res_id = fields.Integer()
    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', default=lambda self: self.env.company, domain=[('system','=','student')])


class StudentClass(models.Model):
    _name = 'res.student.class'
    _description = 'Classes'
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    code = fields.Char()
    res_id = fields.Integer()
    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', default=lambda self: self.env.company, domain=[('system','=','student')])


class StudentFaculty(models.Model):
    _name = 'res.student.faculty'
    _description = 'Faculties'
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    code = fields.Char()
    res_id = fields.Integer()
    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', default=lambda self: self.env.company, domain=[('system','=','student')])


class StudentDepartment(models.Model):
    _name = 'res.student.department'
    _description = 'Departments'
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    code = fields.Char()
    res_id = fields.Integer()
    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', default=lambda self: self.env.company, domain=[('system','=','student')])


class StudentProgram(models.Model):
    _name = 'res.student.program'
    _description = 'Programs'
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    code = fields.Char()
    res_id = fields.Integer()
    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', default=lambda self: self.env.company, domain=[('system','=','student')])


class StudentTerm(models.Model):
    _name = 'res.student.term'
    _description = 'Terms'
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    code = fields.Char()
    res_id = fields.Integer()
    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', default=lambda self: self.env.company, domain=[('system','=','student')])


class StudentBursary(models.Model):
    _name = 'res.student.bursary'
    _description = 'Bursaries'
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    percentage = fields.Float(string='Discount (%)')
    code = fields.Char()
    res_id = fields.Integer()
    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', default=lambda self: self.env.company, domain=[('system','=','student')])

    def name_get(self):
        res = []
        for bursary in self:
            name = '%s - %%%s' % (bursary.name, bursary.percentage)
            res.append((bursary.id, name))
        return res


class StudentPaymentType(models.Model):
    _name = 'res.student.payment.type'
    _description = 'Payment Types'
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    code = fields.Char()
    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', default=lambda self: self.env.company, domain=[('system','=','student')])


class StudentPaymentTemplate(models.Model):
    _name = 'res.student.payment.template'
    _description = 'Student Payment Template'
    _order = 'id desc'

    school_id = fields.Many2one('res.student.school', required=True, ondelete='restrict')
    class_id = fields.Many2one('res.student.class', ondelete='restrict')
    term_id = fields.Many2one('res.student.term', required=True, ondelete='restrict')
    payment_type_id = fields.Many2one('res.student.payment.type', required=True, ondelete='restrict')
    amount = fields.Monetary(required=True)
    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', default=lambda self: self.env.company, domain=[('system','=','student')])
    currency_id = fields.Many2one(related='company_id.currency_id', store=True, readonly=True)
