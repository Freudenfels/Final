# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields,models, _
import requests
import json
from datetime import datetime
from odoo.exceptions import UserError

class ShopifyConfiguration(models.Model):
    _name = "sh.shopify.configuration"
    _description = "Stores Your Shopify Credentials"

    name = fields.Char('Instance')
    sh_api_key = fields.Char("Api Key")
    sh_password = fields.Char("Password")
    sh_secret_key = fields.Char("Secret Key")
    sh_host_name = fields.Char("Host Name")
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    shopify_logger_id = fields.One2many("sh.shopify.log","sh_shopify_id")
    sh_queue_ids = fields.One2many("sh.queue",'sh_current_config')
    
    def generate_vals(self,state,type_,message):
        log_vals = {
                "name" : self.name,
                "sh_shopify_id" : self.id,
                "state" : state,
                "type_" : type_,
                "error" : message,
                "datetime" : datetime.now()
            }
        self.env['sh.shopify.log'].create(log_vals)
    
    def get_headers(self):
        headers = {
            'Content-Type' : 'application/json',
            'X-Shopify-Access-Token' : '%s' %(self.sh_password),
        }
        return headers

    def get_shopify_count(self,objects):
        headers = self.get_headers()
        url = "%s/admin/api/2021-07/%s/count.json" %(self.sh_host_name,objects)        
        response = requests.get(url=url,headers=headers)
        response_json = response.json()        
        if response.status_code == 200:
            response_json = response.json()            
            total = response_json['count']           
            if total == 0:
                return total
            if objects == 'customers' or objects == 'orders':
                total -= total % -500            
            return total
        else:
            return False

    def get_shopify_count_date(self,objects):
        if objects == 'customers':
            past = self.last_sync_contact
        elif objects == 'orders':
            past = self.last_sync_order
        elif objects == 'products':
            past = self.last_sync_product
        past = past.isoformat()
        head, sep, tail = past.partition('.')
        head = head + '+05:00'        
        headers = self.get_headers()
        url = "%s/admin/api/2021-07/%s/count.json?updated_at_min=%s&created_at_min=%s" %(self.sh_host_name,objects,head,head)        
        response = requests.get(url=url,headers=headers)
        response_json = response.json()        
        if response.status_code == 200:
            response_json = response.json()            
            total = response_json['count']            
            return total
            
    def show_popup_failure(self):
        popup_view_id = self.env.ref('sh_shopify_connector.sh_export_failure_view').id
        return {
            'name': _('Notification'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sh.popup.message',                
            'view_id': popup_view_id,
            'target': 'new',
        }

    def show_popup_success(self):
        popup_view_id = self.env.ref('sh_shopify_connector.sh_export_successfull_view').id
        return {
            'name': _('Notification'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sh.popup.message',                
            'view_id': popup_view_id,
            'target': 'new',
        }

    def open_all_contact_queue(self):
        view_id = self.env.ref('sh_shopify_connector.sh_shopify_configuration_queue_tree').id
        return {
            "type": "ir.actions.act_window",
            "name": "Contact Queue",
            "view_mode": "tree",
            "res_model": "sh.queue",
            'view_id': view_id,
            "domain": [],            
        }

    def open_all_order_queue(self):
        view_id = self.env.ref('sh_shopify_connector.sh_shopify_order_queue_tree').id
        return {
            "type": "ir.actions.act_window",
            "name": "Orders Queue",
            "view_mode": "tree",
            "res_model": "sh.queue",
            'view_id': view_id,
            "domain": [],            
        }

    def open_all_product_queue(self):
        view_id = self.env.ref('sh_shopify_connector.sh_shopify_product_queue_tree').id
        return {
            "type": "ir.actions.act_window",
            "name": "Product Queue",
            "view_mode": "tree",
            "res_model": "sh.queue",
            'view_id': view_id,
            "domain": [],            
        }