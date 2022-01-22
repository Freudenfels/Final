# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models, _
import json
import requests
import base64
import re
from datetime import datetime
from odoo.exceptions import UserError
class ShopifyProducts(models.Model):
    _inherit = 'sh.shopify.configuration'

    import_products = fields.Boolean("Import Products")
    auto_import_products = fields.Boolean("Auto Import Products")    
    sh_warehouse_id = fields.Many2one("stock.warehouse",string="Warehouse")
    shopify_primary_location_id = fields.Char("Shopify Primary Location")
    last_sync_product = fields.Datetime("LS Product")   
    page_info = fields.Char()    
    product_import_limit = fields.Integer(string="Import Limit",default="30")
    last_sync_quantity = fields.Datetime("LS Quantity")
    last_product = fields.Char()
    total_count_product = fields.Integer(compute="_compute_product_count")
    also_import_image = fields.Boolean("Import Images")
    shopify_product_category = fields.Many2one('product.category',string="Product Category")
    product_import_between_dates = fields.Boolean("Import Between Dates Product")
    product_from_date = fields.Datetime("From Date Product")
    product_to_date = fields.Datetime("To Date Product")

    def _compute_product_count(self):
        domain = [('queue_type', '=', 'product')]
        total_product = self.env['sh.queue'].search(domain)
        count = 0
        for data in total_product:
            count += 1
        self.total_count_product = count

    def submit_products(self):
        if self.import_products or self.auto_import_products:
            self.sh_inventory_check()
            total_pro = self.get_shopify_count('products')
            if total_pro == 0:
                self.generate_vals("success","product", 'No New Products To Import')
                return
            from_where = 'above'
            self.recall_product_data()

    def recall_product_data(self):
        headers = self.get_headers()
        if self.product_import_between_dates:
            from_head = self.get_head(self.product_from_date)
            to_head = self.get_head(self.product_to_date)
            product_url = "%s/admin/api/2021-07/products.json?fields=id,title&limit=250&created_at_min=%s&created_at_max%s" %(self.sh_host_name,from_head,to_head)                
        elif not self.last_sync_product:
            if not self.last_product:
                product_url = "%s/admin/api/2021-07/products.json?fields=id,title&limit=250&since_id=0" %(self.sh_host_name)
            else:
                product_url = "%s/admin/api/2021-07/products.json?fields=id,title&limit=250&since_id=%s" %(self.sh_host_name,int(self.last_product))
        else:
            head = self.get_head(self.last_sync_product)
            product_url = "%s/admin/api/2021-07/products.json?fields=id,title&limit=250&created_at_min=%s&updated_at_min%s" %(self.sh_host_name,head,head)
        response = requests.get(url=product_url,headers=headers)
        response_json = response.json()
        if response.status_code == 200:            
            response_json = response.json()
            for data in response_json['products']:
                find_in_queue = False
                domain = [('sh_product_id', '=', data['id']),('queue_type', '=', 'product')]                
                find_in_queue = self.env['sh.queue'].search(domain)                    
                if not find_in_queue:
                    queue_vals = {
                        'queue_type' : 'product',    
                        'queue_sync_date' : datetime.now(),
                        'sh_product_id' : data['id'],
                        'sh_current_state' : 'draft',
                        'sh_queue_name' : data['title']
                    }                    
                    self.env['sh.queue'].create(queue_vals)
            if response_json['products']:
                self.last_product = data['id']
                if len(response_json['products']) == 250:
                    self.recall_product_data()
                else:
                    self.generate_vals("success","product", 'Imported Successfully, Products added to the queue')
                    self.last_sync_product = datetime.now()
                    self.last_product = False
            elif len(response_json['products']) == 0:
                self.generate_vals("success","product", 'No New Products To Import')

    def import_single_product(self):
        import_list = []        
        if self.single_product_id:
            import_list.append(self.single_product_id)
            from_where = 'force'
        if import_list:
            self.products_import(import_list,from_where)

    def manage_import_product(self):
        domain = [('company_id', '=', self.env.company.id)]
        find_config = self.env['sh.shopify.configuration'].search(domain)        
        for rec in find_config:            
            domain = [('queue_type', '=', 'product'),('sh_current_state', '=', 'draft')]
            get_con = self.env['sh.queue'].search(domain,order = "id asc",limit=10)        
            import_list = []
            if get_con:
                for data in get_con:
                    import_list.append(data.sh_product_id)
                from_where = 'cron'
                find_config.products_import(import_list,from_where)
            else:
                rec.generate_vals("success","contact","Cron : Imported Successfully")

    def sh_inventory_check(self):
        try:
            headers = {
                'Content-Type' : 'application/json',
                'X-Shopify-Access-Token' : '%s' %(self.sh_password),
            }
            shop_url = "%s/admin/api/2021-07/shop.json" % (self.sh_host_name)
            shop_response = requests.get(url=shop_url,headers=headers)            
            if shop_response.status_code == 200:
                shop_response_json = shop_response.json()                
                self.shopify_primary_location_id = shop_response_json['shop']['primary_location_id']
            inventory_url = "%s/admin/api/2021-07/locations.json" %(self.sh_host_name)
            response = requests.get(url=inventory_url,headers=headers)
            response_json = response.json()            
            if 'locations' in response_json:               
                if len(response_json['locations']) >= 2:
                    group_warehouse_active = self.env.ref('stock.group_stock_multi_warehouses')
                    group_locations_active = self.env.ref('stock.group_stock_multi_locations')
                    self.env.user.write({
                            'groups_id' : [(4,group_warehouse_active.id),(4,group_locations_active.id)]
                        }) 
                for value in response_json['locations']:
                    domain = [('sh_shopify_location_id', '=', value['id'])]
                    find_address = self.env['stock.location'].search(domain)
                    if not find_address:
                        ware_vals = {
                            'sh_shopify_location_id': value['id'],
                            'usage' : 'internal',
                            'location_id' : self.sh_warehouse_id.lot_stock_id.id
                        }                    
                        if int(self.shopify_primary_location_id) == value['id']:
                            ware_vals['shopify_primary_location'] = self.shopify_primary_location_id
                        code = value['name'].partition(' ')[0]                       
                        ware_vals['name'] = code
                        self.env['stock.location'].create(ware_vals)                
                if self.shopify_primary_location_id:
                    domain = [('warehouse_id', '=', self.sh_warehouse_id.id),('name', '=', 'Delivery Orders')]
                    find_picking = self.env['stock.picking.type'].search(domain)                    
                    domain = [('shopify_primary_location', '!=', False)]                    
                    find_location = self.env['stock.location'].search(domain)                    
                    if find_picking and find_location:                       
                        vals ={
                            'default_location_src_id' : find_location.id
                        }
                        find_picking.write(vals)
        except Exception as e:
            self.generate_vals("error",'product',e)    

    def products_import(self,import_values,from_where):
        try:
            if import_values:
                self.single_product_id = False
                headers = self.get_headers()
                check_count = 0
                for productid in import_values:                
                    check_count += 1
                    product_url = "%s/admin/api/2021-07/products/%s.json" %(self.sh_host_name,productid)
                    response = requests.get(url=product_url,headers=headers)
                    if response.status_code == 200:
                        response_json = response.json()                    
                        if 'product' in response_json:
                            data = response_json['product']                       
                            vals = {
                                'type' : 'product',
                                'name' : data['title'],
                                'taxes_id' : self.company_id.account_sale_tax_id,
                                'supplier_taxes_id' : self.company_id.account_purchase_tax_id,
                            }
                            if self.shopify_product_category:
                                vals['categ_id'] = self.shopify_product_category.id
                            already_created = False
                            domain = [('sh_shopify_product_id', '=', data['id'])]
                            already_created = self.env['product.template'].search(domain)
                            if data['body_html']:
                                remove_html = re.compile('<.*?>')
                                description = re.sub(remove_html, '', data['body_html'])
                                vals['description'] = description
                            if data['tags']:
                                tags = data['tags'].split(',')
                                tag_list = []
                                for tag in tags:                            
                                    domain = [('name', '=', tag)]
                                    find_tags = self.env['sh.product.tag'].search(domain)
                                    if find_tags:
                                        tag_list.append(find_tags.id)
                                    else:
                                        create_tags = self.env['sh.product.tag'].create({'name':tag})                               
                                        tag_list.append(create_tags.id)
                                vals['sh_product_tag_ids'] =  tag_list
                            attr_vals_list = []
                            variant_count = 0
                            for value in data['options']:
                                if value['name'] != 'Title':
                                    variant_count += 1
                                    domain = [('name', '=', value['name'])]
                                    get_attr = self.env['product.attribute'].search(domain,limit=1)
                                    if get_attr:
                                        attr_line_vals = {
                                            'attribute_id' : get_attr.id
                                        }
                                        value_list = []
                                        value_name = []
                                        for xyz in get_attr.value_ids:
                                            for res in value['values']:                                        
                                                if xyz.name == res:                                            
                                                    value_name.append(xyz.name)
                                        new_list = []
                                        for res in value['values']:
                                            if res not in value_name:
                                                a_dict = {
                                                    'name' : res
                                                }
                                                new_list.append((0,0,a_dict))
                                        get_attr.write({'value_ids':new_list})
                                        for xyz in get_attr.value_ids:
                                            for res in value['values']:                                        
                                                if xyz.name == res:
                                                    value_list.append(xyz.id)                                            
                                        attr_line_vals['value_ids'] = value_list 
                                    else:                            
                                        attribute_vals = {
                                            'name' : value['name']
                                        }  
                                        valeu = []                          
                                        attr_list = []
                                        for res in value['values']:                                    
                                            a_line_vals = {
                                                'name' : res
                                            }   
                                            valeu.append(res)                 
                                            attr_list.append((0, 0, a_line_vals))
                                        attribute_vals['value_ids'] = attr_list                                
                                        create_attribute = self.env['product.attribute'].create(attribute_vals)                                            
                                        attr_line_vals = {
                                            'attribute_id' : create_attribute.id,
                                            'value_ids' : create_attribute.value_ids.ids
                                        }                                
                                    if not already_created:
                                        attr_vals_list.append((0, 0, attr_line_vals))                    
                            for rec in data['variants']:
                                if variant_count == 0:                           
                                    vals['list_price'] = rec['price']
                                    vals['default_code'] = rec['sku']                            
                                elif attr_vals_list:                            
                                    vals['attribute_line_ids'] = attr_vals_list                    
                            product_value = ''
                            if already_created:                        
                                product_value = already_created
                                already_created.write(vals)
                            else:
                                if rec['barcode']:
                                    vals['barcode'] = rec['barcode']
                                vals['sh_shopify_product_id'] = data['id']                        
                                create_product = self.env['product.template'].create(vals)                        
                                product_value = create_product
                                if variant_count != 0:
                                    create_product.write({'list_price': '0.00'})                   
                            for rec in data['variants']:
                                for value in product_value.product_variant_ids:
                                    if not rec['title'] == 'Default Title':
                                        check = ''
                                        check1 = ''
                                        for data in value.product_template_attribute_value_ids:
                                            check += data.name +" / "
                                        for data in reversed(value.product_template_attribute_value_ids):
                                            check1 += data.name +" / "
                                        if check or check1:
                                            check = check[:-2].strip()
                                            check1 = check1[:-2].strip()                                        
                                            value.product_template_attribute_value_ids.write
                                            if check == rec['title'] or check1 == rec['title']:
                                                vals = {
                                                    'default_code' : rec['sku'],
                                                    'sh_shopify_product_variant_id' : rec['id'],
                                                    'sh_shopify_price' : rec['price'],
                                                    'sh_shopify_name' : rec['title'],
                                                    'sh_shopify_inventory_id' : rec['inventory_item_id']
                                                }
                                                if rec['barcode']:                                        
                                                    if value.barcode == rec['barcode']:                                            
                                                        pass
                                                    else:                                            
                                                        vals['barcode'] = rec['barcode']
                                                value.write(vals)                                        
                                    else:
                                        vals = {
                                            'sh_shopify_inventory_id' : rec['inventory_item_id']
                                        }
                                        value.write(vals)
                            self.get_quantity(product_value)
                            if self.also_import_image:
                                if response_json['product']['images']:                            
                                    for image in response_json['product']['images']:                                
                                        domain = [('sh_shopify_product_id', '=', image['product_id'])]
                                        find_product = self.env['product.template'].search(domain)
                                        binary = base64.b64encode(requests.get(image['src']).content)
                                        if len(image['variant_ids']) != 0:
                                            for shopify_variant in image['variant_ids']:                                    
                                                domain = [('sh_shopify_product_variant_id', '=', shopify_variant)]
                                                find_variant = self.env['product.product'].search(domain)                                    
                                                if find_variant:
                                                    find_variant.write({'image_1920': binary})
                                        if find_product:
                                            image_vals = {
                                                'type' : 'url',
                                                'url' : image['src'],
                                                'name' : 'Attachment',
                                                'res_model' : 'product.template',
                                                'res_id' : find_product.id
                                            }                                    
                                            domain = [('sh_shopify_attachment_id', '=', image['id'])]
                                            find_image = self.env['ir.attachment'].search(domain)
                                            if not find_image:
                                                image_vals['sh_shopify_attachment_id'] = image['id']
                                                create_image = self.env['ir.attachment'].create(image_vals)
                                if response_json['product']['image']:
                                    domain = [('sh_shopify_product_id', '=', response_json['product']['image']['id'])]
                                    find_product = self.env['product.template'].search(domain)
                                    if find_product:
                                        binary = base64.b64encode(requests.get(response_json['product']['image']['src']).content)
                                        find_product.write({'image_1920': binary})
                    domain = [('sh_product_id', '=', productid),('queue_type', '=', 'product')]
                    get_that_product = self.env['sh.queue'].search(domain)                
                    if get_that_product:
                        get_that_product.unlink()  
                if from_where == 'force':                
                    self.generate_vals("success","product","Imported Successfully")
                    return self.show_popup_success()
                else:                      
                    self.generate_vals("success","product","Cron : Partially Imported") 
        except Exception as e:
            self.generate_vals("error",'product',e)
    
    def get_quantity_by_cron(self):
        domain = [('company_id', '=', self.env.company.id)]
        find_config = self.env['sh.shopify.configuration'].search(domain)
        find_config.get_quantity()

    def get_quantity(self,main_product):        
        headers = self.get_headers()
        inventory_list = [pro_var.sh_shopify_inventory_id for pro_var in main_product.product_variant_ids if pro_var.sh_shopify_inventory_id]
        inventory_string = ','.join(inventory_list)        
        if not self.page_info:
            inventoryLevels_url = "%s/admin/api/2021-07/inventory_levels.json?limit=250&inventory_item_ids=%s" %(self.sh_host_name,inventory_string)
        else:
            inventoryLevels_url = "%s/admin/api/2021-07/inventory_levels.json?limit=250&page_info=%s" %(self.sh_host_name,self.page_info)            
        response = requests.get(headers=headers,url=inventoryLevels_url)
        if response.status_code == 200:
            response_json = response.json()        
            link = response.headers.get('Link')
            if link:
                for page_link in link.split(','):
                    if page_link.find('next') > 0:
                        self.page_info = page_link.split(';')[0].strip('<>').split('page_info=')[1]
            if 'inventory_levels' in response_json and len(response_json['inventory_levels']) != 0:            
                for data in response_json['inventory_levels']:
                    domain = [('sh_shopify_inventory_id', '=', data['inventory_item_id'])]
                    find_product = self.env['product.product'].search(domain)                
                    if find_product:                    
                        domain = [('sh_shopify_location_id', '=', data['location_id'])]
                        storage_location = self.env['stock.location'].search(domain)                    
                        domain = [('product_id', '=', find_product.id),('location_id', '=', storage_location.id)]
                        find_quant = self.env['stock.quant'].search(domain)
                        final_quantity = 0                   
                        if find_quant:                        
                            for quant in find_quant:                            
                                if data['available'] != quant.quantity and data['available'] > quant.quantity:
                                    final_quantity = data['available'] - quant.quantity
                        elif data['available']:
                            final_quantity = data['available']
                        if final_quantity >= 0:
                            qty_vals = {
                                'product_id' : find_product.id,
                                'product_tmpl_id' : find_product.product_tmpl_id.id,
                            }   
                            if not self.user_has_groups('stock.group_stock_multi_locations'):                        
                                qty_vals.update({
                                    'new_quantity' : final_quantity,  
                                })
                                created_qty_on_hand = self.env['stock.change.product.qty'].create(qty_vals)
                                if created_qty_on_hand:
                                    created_qty_on_hand.change_product_qty()
                            else:
                                qty_vals.update({                      
                                    'location_id' : storage_location.id,
                                    'quantity' : final_quantity
                                })
                                created_qty_on_hand = self.env['stock.quant'].sudo().create(qty_vals)            

    def _shopify_product_cron(self):
        domain = []
        find_config = self.env['sh.shopify.configuration'].search(domain)
        for data in find_config:
            if data.auto_import_products:
                data.submit_products()