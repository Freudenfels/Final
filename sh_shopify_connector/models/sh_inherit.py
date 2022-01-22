# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models, api

class ShopifyContacts(models.Model):
    _inherit = 'res.partner'

    sh_shopify_contact_id = fields.Char("Shopify Contact")
    sh_shopify_location_id = fields.Char("Shopify Location")

    shh_firstname = fields.Char("Firstname")
    shh_lastname = fields.Char("Lastname")
    @api.onchange('shh_firstname','shh_lastname')
    def onchange_first_last_name(self):        
        if self.shh_lastname:
            self.name = self.shh_firstname + ' ' + self.shh_lastname
        else:
            self.name = self.shh_firstname

class ShopifyProducts(models.Model):
    _inherit = 'product.template'

    sh_shopify_product_id = fields.Char("Shopify Product")
    def export_shopify_product(self):
        active_product_ids = self.env['product.template'].browse(self.env.context.get('active_ids'))
        domain = [('company_id', '=', self.env.company.id)]        
        find_config =  self.env['sh.shopify.configuration'].search(domain)        
        res = find_config.final_products_export(active_product_ids)
        return res
        
class ShopifyAttribute(models.Model):
    _inherit = 'product.attribute'

    sh_shopify_attribute_id = fields.Char("Shopify Attribute")

class ShopifyVariant(models.Model):
    _inherit = 'product.product'

    sh_shopify_product_variant_id = fields.Char("Shopify Variant")
    sh_shopify_name = fields.Char("Mix Name")
    sh_shopify_price = fields.Float("Shopify Price")
    sh_shopify_inventory_id = fields.Char("Shopify Inventory")

    def _compute_product_price_extra(self):
        for product in self:
            if product.sh_shopify_product_variant_id:
                product.price_extra = product.sh_shopify_price
            else:
                product.price_extra = sum(product.product_template_attribute_value_ids.mapped('price_extra'))
class ShopifyAttachment(models.Model):
    _inherit = 'ir.attachment'

    sh_shopify_attachment_id = fields.Char("Shopify Attachment")

class ShopifySaleOrder(models.Model):
    _inherit = 'sale.order'

    sh_shopify_draft_order_id = fields.Char("Shopify Sale Order")
    sh_shopify_order_id = fields.Char("Shopify Orders")
    sh_shopify_order_name = fields.Char("Shopify Order No")
    sh_shopify_configuration_id = fields.Many2one("sh.shopify.configuration",string="Shopify Configuration")
    shopify_cn_number = fields.Char("CN Number")
    def cancel_reason_wizard(self):
        return {
            'name':'Cancel Reason',
            'res_model': 'sh.shopify.cancel.reason',
            'view_mode':'form',
            'view_id': self.env.ref('sh_shopify_connector.sh_shopify_cancel_reason_form').id,
            'target':'new',
            'type':'ir.actions.act_window'
        }

    def manually_update_orders(self):
        domain = []
        find_config = self.env['sh.shopify.configuration'].search(domain)
        active_sale_order_ids = self.env['sale.order'].browse(self.env.context.get('active_ids'))
        update_list = []
        for data in active_sale_order_ids:
            if data.state == 'draft' or data.state == 'sent':
                update_list.append(data.sh_shopify_order_id)
        if update_list:
            find_config.sh_import_orders(update_list,'force')
    
    def manually_confirm_shopify_orders(self):
        active_sale_order_ids = self.env['sale.order'].browse(self.env.context.get('active_ids'))
        for orders in active_sale_order_ids:
            orders.action_confirm()
class ShopifySaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sh_shopify_order_line_id = fields.Char("Shopify Order Line")

class ProductTemplateAttributeShopify(models.Model):
    _inherit = 'product.template.attribute.value'

    sh_product_title_name = fields.Char("Product Title")

class ShopifyStockLocation(models.Model):
    _inherit = 'stock.location'

    sh_shopify_location_id = fields.Char("Shopify Location")
    shopify_primary_location = fields.Char("Default")

class MoveLine(models.Model):
    _inherit = 'account.move.line'

    sh_refund_qty = fields.Float("Refundable Quantity",related="quantity")
    sh_refund_price = fields.Float("Refundable Price",related="price_unit")
class ShopifyInvoiceRefund(models.Model):
    _inherit = 'account.move'

    sh_refund_success = fields.Boolean()
    def shopify_refund_wizard(self):        
        action = {
            'name':'Shopify Refund',
            'res_model': 'sh.shopify.refund',
            'view_mode':'form',
            'view_id': self.env.ref('sh_shopify_connector.sh_shopify_refunds_form').id,
            'target':'new',
            'type':'ir.actions.act_window'
        }
        context = {
            'default_sh_amount_total' : self.amount_total,
            'default_sh_amount_untaxed' : self.amount_untaxed,
            'default_currency_id' : self.currency_id.id,
            'default_sh_tax_amount' : self.amount_tax,
            'default_sh_send_refund_amount' : self.amount_total
        }
        list_lines = []       
        if self.invoice_line_ids:
            context.update({
                'default_sh_invoice_line_ids':self.invoice_line_ids.ids,
                })
        action['context'] = context   
        return action