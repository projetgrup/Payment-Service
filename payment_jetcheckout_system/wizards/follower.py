# -*- coding: utf-8 -*-
from odoo import models, fields


class PayloxPartnerFollower(models.TransientModel):
    _name = 'paylox.partner.follower'
    _description = 'Partner Follower'

    follower_ids = fields.Many2many('res.partner', string='Followers')
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def confirm(self):
        pids = self.env.context.get('active_ids')
        partners = self.env['res.partner'].browse(pids)
        if self.env.context.get('add'):
            method = 'message_subscribe'
        elif self.env.context.get('remove'):
            method = 'message_unsubscribe'
        else:
            return
        for partner in partners:
            getattr(partner, method)(self.follower_ids.ids)
