# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models, _
import json
import requests
from dateutil import parser
import pytz
from datetime import datetime
utc = pytz.utc
from odoo.exceptions import UserError
class ShopifyDraftOrders(models.Model):
    _inherit = 'sh.shopify.configuration'
    
    import_orders = fields.Boolean("Import Orders")
    import_draft_orders = fields.Boolean("Import Draft Orders")
    auto_import_draft_orders = fields.Boolean("Auto Import Draft ORders")
    auto_import_orders = fields.Boolean("Auto Import Orders")
    sh_total_orders = fields.Integer()
    sh_total_half_orders = fields.Integer()
    all_orders_imported = fields.Boolean()
    last_sync_order_date = fields.Boolean()
    order_count = fields.Integer()
    single_product_id = fields.Char()
    last_order = fields.Char()
    last_sync_order = fields.Datetime()
    import_order_after = fields.Date("Import After")
    total_count_orders = fields.Integer(compute="_compute_orders_count")    
    sh_confirm_order = fields.Boolean("Confirm Order")
    order_import_between_dates = fields.Boolean("Import Between Dates Orders")
    order_from_date = fields.Datetime("From Date Orders")
    order_to_date = fields.Datetime("To Date Orders")

    def _compute_orders_count(self):
        domain = [('queue_type', '=', 'order')]
        total_orders = self.env['sh.queue'].search(domain)
        count = 0
        for data in total_orders:
            count += 1
        self.total_count_orders = count

    def submit_draft_orders(self):      
        if self.import_orders or self.auto_import_orders:            
            if not self.sh_total_orders:
                if not self.last_sync_order:
                    total_count = self.get_shopify_count('orders')
                else:
                    total_count = self.get_shopify_count_date('orders')
                if total_count == 0:
                    self.generate_vals("success","orders", 'No New Orders To Import')
                if total_count:
                    self.all_orders_imported = False
                    self.sh_total_orders = total_count
                    if total_count > 15000:
                        if self.order_count == 0:
                            self.sh_total_half_orders = 5000
            self.recall_order_data()            

    def recall_order_data(self):
        try:            
            headers = self.get_headers()
            if self.order_import_between_dates:
                from_head = self.get_head(self.order_from_date)
                to_head = self.get_head(self.order_to_date)
                if not self.last_order:
                    draft_utl = "%s/admin/api/2021-07/orders.json?fields=id,name&limit=250&since_id=0&created_at_min=%s&created_at_max=%s" %(self.sh_host_name,from_head,to_head)
                else:
                    draft_utl = "%s/admin/api/2021-07/orders.json?fields=id,name&limit=250&since_id=%s&created_at_min=%s&created_at_max=%s" %(self.sh_host_name,int(self.last_order),from_head,to_head)
            elif not self.last_sync_order:
                if not self.last_order:
                    draft_utl = "%s/admin/api/2021-07/orders.json?fields=id,name&limit=250&since_id=0" %(self.sh_host_name)
                else:
                    draft_utl = "%s/admin/api/2021-07/orders.json?fields=id,name&limit=250&since_id=%s" %(self.sh_host_name,int(self.last_order))
            else:
                head = self.get_head(self.last_sync_order)
                if not self.last_order:
                    draft_utl = "%s/admin/api/2021-07/orders.json?fields=id,name&limit=250&since_id=0&updated_at_min=%s&created_at_min=%s" %(self.sh_host_name,head,head)
                else:
                    draft_utl = "%s/admin/api/2021-07/orders.json?fields=id,name&limit=250&since_id=%s&updated_at_min=%s&created_at_min=%s" %(self.sh_host_name,int(self.last_order),head,head)           
            response = requests.get(url=draft_utl,headers=headers)
            response_json = response.json()            
            if 'orders' in response_json:
                if response_json['orders']: 
                    self.order_count += 250
                    for data in response_json['orders']:
                        find_in_queue = False
                        domain = [('sh_order_id', '=', data['id']),('queue_type', '=', 'order')]
                        find_in_queue = self.env['sh.queue'].search(domain)
                        if not find_in_queue:
                            queue_vals = {
                                'queue_type' : 'order',
                                'queue_sync_date' : datetime.now(),
                                'sh_order_id' : data['id'],
                                'sh_current_state' : 'draft',
                                'sh_queue_name' : data['name']
                            }
                            self.env['sh.queue'].create(queue_vals)
                    self.last_order = 0               
                    self.last_order = data['id']            
                    if self.order_count == self.sh_total_orders:
                        self.generate_vals("success","orders", 'Imported Successfully, Orders added to the queue')
                        self.order_count = 0
                        self.last_order = 0
                        self.sh_total_orders = 0 
                        self.last_sync_order = datetime.now()                       
                        self.sh_total_half_orders = 0
                        return
                    elif self.order_count == self.sh_total_half_orders:
                        self.sh_total_half_orders += 5000
                        self.generate_vals("success","orders", 'Partially Imported, Import Again')
                        return
                    if len(response_json['orders']) == 250:
                        self.recall_order_data()
                    else:
                        self.generate_vals("success","orders", 'Imported Successfully, Orders added to the queue')
                        self.order_count = 0
                        self.last_order = 0
                        self.sh_total_orders = 0 
                        self.last_sync_order = datetime.now()                       
                        self.sh_total_half_orders = 0
                elif len(response_json['orders']) == 0:                   
                    self.generate_vals("success","orders", 'No New Orders To Import')
                    return
                else:
                    self.generate_vals("error","orders", 'Failed, Something Went Wrong')
                    self.last_order = 0
                    self.order_count = 0
                    self.sh_total_orders = 0
                    self.sh_total_half_orders = 0
        except Exception as e:
            self.generate_vals("error","orders", e)

    def manage_import_order(self):
        domain = []
        find_config = self.env['sh.shopify.configuration'].search(domain)       
        for rec in find_config:            
            if not rec.all_orders_imported:            
                domain = [('queue_type', '=', 'order'),('sh_current_state', '=', 'draft')]
                get_orders = self.env['sh.queue'].search(domain,order = "id asc",limit=2)
                import_list = []
                if get_orders:
                    for data in get_orders:
                        import_list.append(data.sh_order_id)
                    from_where = 'normal'
                    rec.sh_import_orders(import_list,from_where)
                else:
                    rec.all_orders_imported = True
                    rec.generate_vals("success","orders","Cron : Imported Successfully")

    def sh_import_orders(self,import_list,from_where):
        try:
            headers = {
                'Content-Type' : 'application/json',
                'X-Shopify-Access-Token' : '%s' %(self.sh_password),
            }
            check_count = 0
            for orderid in import_list:            
                check_count += 1
                order_url = "%s/admin/api/2021-07/orders/%s.json?limit=250&fields=id,currency,billing_address,name,note,order_number,gateway,location_id,tags,customer,line_items,refunds,financial_status,created_at,discount_applications,tax_lines,fulfillment_status,shipping_lines,shipping_address" %(self.sh_host_name,orderid)
                response = requests.get(url=order_url,headers=headers)
                response_json = response.json()                
                if 'order' in response_json:                    
                    data = response_json['order']
                    type_of = 'orders'
                    self.generate_sale_order_vals(data,type_of)
                    domain = [('sh_order_id', '=', orderid),('queue_type', '=', 'order')]
                    get_that_order = self.env['sh.queue'].search(domain)              
                    if get_that_order:
                        get_that_order.unlink()            
            if from_where == 'force':
                self.generate_vals("success","orders","Imported Successfully")
                return self.show_popup_success()
            else:
                self.generate_vals("success","orders","Cron : Partially Imported")
        except Exception as e:            
            self.generate_vals('error','orders',e)

    def generate_sale_order_vals(self,data,type_of):
        total_discount = 0.0
        if 'applied_discount' in data:
            if data['applied_discount']:
                if data['applied_discount']['value_type'] == 'percentage':
                    total_discount += float(data['applied_discount']['value'])
        elif 'discount_applications' in data:
            if data['discount_applications']:
                for values in data['discount_applications']:
                    if values['value_type'] == 'percentage':
                        total_discount += float(values['value'])
        if data['tax_lines']:                        
            for value in data['tax_lines']:
                rate = float(value.get('rate', 0.0))
                rate *= 100
                tax_vals = {
                    'name' : value['title'],
                    'amount' : float(rate),
                    'type_tax_use' : 'sale',                    
                }
                domain = [('name', '=', value['title']),('type_tax_use', '=', 'sale'),('amount', '=', float(rate))]
                find_tax = self.env['account.tax'].search(domain)
                if not find_tax:
                    self.env['account.tax'].create(tax_vals)
        date_order = parser.parse(data['created_at']).astimezone(utc).strftime('%Y-%m-%d %H:%M:%S')
        vals = {
            'sh_shopify_order_name' : data['name'],
            'note' : data['note'],
            'date_order' : date_order,
            'sh_shopify_configuration_id' : self.id
        }    
        shipping_number = self.get_shipping_number(data['id'])        
        if shipping_number:
            vals['shopify_cn_number'] = shipping_number
        partner = False
        if 'customer' in data:
            domain = [('sh_shopify_contact_id', '=', data['customer']['id'])]
            find_partner = self.env['res.partner'].search(domain)            
            if find_partner:                
                partner = find_partner.id
            else:
                cust_id = []
                cust_id.append(data['customer']['id'])
                self.contact_import(cust_id,'force')
                domain = [('sh_shopify_contact_id', '=', data['customer']['id'])]
                find_partner = self.env['res.partner'].search(domain)            
                if find_partner:                
                    partner = find_partner.id
            if partner:
                vals['partner_id'] = partner
                if find_partner.workflow_id:
                    vals['workflow_id'] = find_partner.workflow_id.id
                ship_count = 0
                bill_count = 0
                if 'default_address' in data['customer']:
                    if data['customer']['default_address']['address1'] != data['shipping_address']['address1'] and data['customer']['default_address']['city'] != data['shipping_address']['city']:
                        ship_count += 1
                    if data['customer']['first_name'] != data['shipping_address']['first_name']:
                        ship_count += 1
                    if ship_count != 0:
                        ship_name = data['shipping_address']['name']
                        domain = [('name', '=', ship_name)]
                        already_ship = self.env['res.partner'].search(domain,limit=1)
                        if not already_ship:
                            ship_vals = self.generate_shipiing_address(data['shipping_address'])                        
                            ship_vals['parent_id'] = partner
                            ship_vals['type'] = 'delivery'                        
                            create_ship_address = self.env['res.partner'].create(ship_vals)
                            vals['partner_shipping_id'] = create_ship_address.id
                        else:
                            vals['partner_shipping_id'] = already_ship.id
                    if 'billing_address' in data:
                        if data['customer']['default_address']['address1'] != data['billing_address']['address1'] and data['customer']['default_address']['city'] != data['billing_address']['city']:
                            bill_count += 1
                        if data['customer']['first_name'] != data['billing_address']['first_name']:
                            bill_count += 1
                        if bill_count != 0:
                            bill_name = data['billing_address']['name']
                            domain = [('name', '=', bill_name)]
                            already_bill = self.env['res.partner'].search(domain,limit=1)
                            if not already_bill:
                                bill_vals = self.generate_shipiing_address(data['billing_address'])                        
                                bill_vals['parent_id'] = partner
                                bill_vals['type'] = 'invoice'                        
                                create_bill_address = self.env['res.partner'].create(bill_vals)
                                vals['partner_invoice_id'] = create_bill_address.id
                            else:
                                vals['partner_invoice_id'] = already_bill.id        
        if not 'workflow_id' in vals and self.company_id.workflow_id:
            vals['workflow_id'] = self.company_id.workflow_id.id
        line_vals_list = []
        for rec in data['line_items']:
            domain = [('sh_shopify_order_line_id', '=', rec['id'])]
            already_sale_order_line = self.env['sale.order.line'].search(domain)
            if already_sale_order_line:
                for sale_order_line in already_sale_order_line:
                    sale_order_line.unlink()
            line_vals = {}
            disc = 0
            if 'applied_dicount' in rec:
                if rec['applied_discount']:               
                    if rec['applied_discount']['value_type'] == 'percentage':
                        disc = float(rec['applied_discount']['value'])        
            if disc:
                line_vals['discount'] = disc + total_discount
            else:
                line_vals['discount'] = total_discount
            if rec['variant_id']:                        
                domain = [('sh_shopify_product_variant_id', '=', rec['variant_id'])]
                find_variant = self.env['product.product'].search(domain)
                if find_variant:
                    line_vals['product_id'] = find_variant.id
            if not 'product_id' in line_vals and rec['product_id']:
                domain = [('sh_shopify_product_id', '=', rec['product_id'])]
                find_product = self.env['product.template'].search(domain)
                if find_product:
                    line_vals['product_id'] = find_product.product_variant_id.id
            if not 'product_id' in line_vals and rec['product_id']:
                self.single_product_id = rec['product_id']
                self.import_single_product()
                if rec['variant_id']:
                    domain = [('sh_shopify_product_variant_id', '=', rec['variant_id'])]
                    find_variant = self.env['product.product'].search(domain)
                    if find_variant:
                        line_vals['product_id'] = find_variant.id
                if not 'product_id' in line_vals and rec['product_id']:
                    domain = [('sh_shopify_product_id', '=', rec['product_id'])]
                    find_product = self.env['product.template'].search(domain)
                    if find_product:
                        line_vals['product_id'] = find_product.product_variant_id.id
            if rec['tax_lines']:
                tax_list = []
                for res in rec['tax_lines']:
                    rate = float(res.get('rate', 0.0))
                    rate *= 100
                    domain = [('name', '=', res['title']),('amount', '=', rate),('type_tax_use', '=', 'sale')]
                    get_tax = self.env['account.tax'].search(domain)
                    if get_tax:
                        tax_list.append(get_tax.id)
                line_vals['tax_id'] = tax_list
            line_vals['product_uom_qty'] = rec['quantity']
            line_vals['price_unit'] = rec['price']        
            if 'product_id' in line_vals:
                line_vals['sh_shopify_order_line_id'] = rec['id']
                line_vals_list.append((0, 0, line_vals))
        if data['shipping_lines']:
            for ship in data['shipping_lines']:
                domain = [('sh_shopify_order_line_id', '=', ship['id'])]
                find_line = self.env['sale.order.line'].search(domain)
                if find_line:
                    for shi_line in find_line:
                        shi_line.unlink()
                if float(ship['price']) > 0.00:
                    product = self.get_shopify_shipping()
                    ship_vals = {
                        'product_id' : product,
                        'product_uom_qty' : 1,
                        'price_unit' : ship['price'],
                    }
                    ship_vals['sh_shopify_order_line_id'] = ship['id']
                    line_vals_list.append((0, 0, ship_vals))
        if line_vals_list:
            vals['order_line'] = line_vals_list        
        if partner:
            if type_of == 'draft_orders':
                domain = [('sh_shopify_draft_order_id', '=', data['id'])]
                find_order = self.env['sale.order'].search(domain)
                if find_order:
                    find_order.write(vals)
                    create_order = find_order
                else:
                    vals['sh_shopify_draft_order_id'] = data['id']
                    create_order = self.env['sale.order'].create(vals)
            elif type_of == 'orders':
                domain = [('sh_shopify_order_id', '=', data['id'])]
                find_order = self.env['sale.order'].search(domain)               
                if find_order:
                    find_order.write(vals)
                    create_order = find_order
                else:
                    vals['sh_shopify_order_id'] = data['id']
                    create_order = self.env['sale.order'].create(vals)
            if self.sh_confirm_order:
                create_order.action_confirm()
        if data['refunds']:
            for refund in data['refunds']:
                if 'refund_line_items' in refund:
                    for refund_line in refund['refund_line_items']:
                        domain = [('sh_shopify_order_line_id', '=', refund_line['line_item_id'])]
                        find_refund_line = self.env['sale.order.line'].search(domain)
                        if find_refund_line:
                            find_refund_line.unlink()
    def generate_shipiing_address(self,value):
        vals = {            
            'name' : value['name'],
            'street' : value['address1'] if value['address1'] else '',
            'street2' : value['address2'] if value['address2'] else '',
            'city' : value['city'] if value['city'] else '',
            'zip' : value['zip'] if value['zip'] else '',
            'phone' : value['phone'] if value['phone'] else '',
        }        
        if value['province']:
            domain = [('name', '=', value['province'])]
            find_state = self.env['res.country.state'].search(domain)
            if find_state:
                vals['state_id'] = find_state.id
                vals['country_id'] = find_state.country_id.id
        if not 'country_id' in vals:
            if value['country']:
                domain = [('name', '=', value['country'])]
                find_country = self.env['res.country'].search(domain)
                if find_country:
                    vals['country_id'] = find_country.id
                    if not 'state_id' in vals:
                        for state in find_country.state_ids:
                            if value['province'] == state.name:
                                vals['state_id'] = state.id
                                break
                else:
                    create_country = self.env['res.country'].create({'name':value['country']})
                    vals['country_id'] = create_country.id
        return vals

    def get_shipping_number(self,order_no):       
        url = "%s/admin/api/2021-07/orders/%s/fulfillments.json" %(self.sh_host_name,order_no)
        headers = self.get_headers()
        number = ''
        response = requests.get(url=url,headers=headers)
        if response.status_code == 200:
            response_json = response.json()
            for data in response_json['fulfillments']:
                number = data['tracking_number']
        return number

    def _shopify_orders_cron(self):
        domain = []
        find_config = self.env['sh.shopify.configuration'].search(domain)
        for data in find_config:
            if data.auto_import_orders:
                data.submit_draft_orders()

    def get_shopify_shipping(self):
        domain = [('name', '=', 'Shopify Deliver Charges'),('type', '=', 'service')]
        find_pro = self.env['product.template'].search(domain)
        if find_pro:
            product = find_pro.product_variant_id.id
        else:
            vals = {
                'name' : 'Shopify Deliver Charges',
                'type' : 'service',
                'taxes_id' : False,            
            }
            create_pro = self.env['product.template'].create(vals)
            product = create_pro.product_variant_id.id
        return product
    
    def _shopify_tracking_number_cron(self):
        domain = []
        find_config = self.env['sh.shopify.configuration'].search(domain)
        for rec in find_config:
            domain = [('shopify_cn_number', '=', False),('sh_shopify_order_id', '!=', False),('state', '!=', 'cancel')]
            non_cn_number = self.env['sale.order'].search(domain)
            if non_cn_number:
                for data in non_cn_number:
                    number = rec.get_shipping_number(data.sh_shopify_order_id)
                    if number:
                        data.write({'shopify_cn_number':number})
