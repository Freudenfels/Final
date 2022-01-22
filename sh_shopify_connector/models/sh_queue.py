# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models

class ShopifyQueue(models.Model):
    _name = 'sh.queue'
    _description = 'Helps you to add incoming req in queue'
    _order = 'id desc'

    queue_type = fields.Selection([('contact','Contact'),('product','Products'),('order','Orders')])
    sh_contact_id = fields.Char("Contacts")
    sh_queue_name = fields.Char("Name")
    sh_product_id = fields.Char("Products")
    sh_order_id = fields.Char("Orders")
    queue_sync_date = fields.Datetime("Sync Date-Time")
    sh_current_config = fields.Many2one('sh.shopify.configuration')
    sh_current_state = fields.Selection([('draft','Draft'),('done','Done')],string="State")


    def import_shopify_manually(self):
        active_queue_ids = self.env['sh.queue'].browse(self.env.context.get('active_ids'))
        domain = [('company_id', '=', self.env.company.id)]        
        find_config =  self.env['sh.shopify.configuration'].search(domain)        
        res = find_config.manually_from_queue(active_queue_ids)
        return res