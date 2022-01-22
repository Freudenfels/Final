# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models

class SalesforceLogger(models.Model):
    _name = 'sh.shopify.log'
    _description = 'Helps you to maintain the activity done'
    _order = 'id desc'

    name = fields.Char("Name")
    error = fields.Char("Message")
    datetime = fields.Datetime("Date & Time")
    sh_shopify_id = fields.Many2one('sh.shopify.configuration')
    state = fields.Selection([('success','Success'),('error','Failed')])
    type_ = fields.Selection([('contact','Contacts'),('product','Products'),('draft_orders','Draft Orders'),('orders','Orders')])