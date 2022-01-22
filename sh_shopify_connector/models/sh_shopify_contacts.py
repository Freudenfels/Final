# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models, _
import json
import requests
from odoo.exceptions import UserError
from datetime import datetime
class ShopifyContacts(models.Model):
    _inherit = 'sh.shopify.configuration'

    import_contact = fields.Boolean("Import Contacts")
    auto_import_contact = fields.Boolean("Auto Import Contacts")

    sh_total_customer = fields.Integer()
    sh_total_half_customer = fields.Integer()
    all_contacts_imported_successfully = fields.Boolean()    
    cust_count = fields.Integer()
    cust_last_count = fields.Char()
    last_sync_contact = fields.Datetime()
    total_count_contact = fields.Integer(compute="_compute_contact_count")    
    contact_import_between_dates = fields.Boolean("Import Between Dates Contact")
    contact_from_date = fields.Datetime("From Date Contact")
    contact_to_date = fields.Datetime("To Date Contact")

    def _compute_contact_count(self):
        domain = [('queue_type', '=', 'contact')]
        total_contact = self.env['sh.queue'].search(domain)
        count = 0
        for data in total_contact:
            count += 1
        self.total_count_contact = count

    def submit_contact(self):
        if self.import_contact or self.auto_import_contact:
            if not self.sh_total_customer:
                if not self.last_sync_contact:
                    total_count = self.get_shopify_count('customers')
                else:
                    total_count = self.get_shopify_count_date('customers')                    
                if total_count == 0:
                    self.generate_vals("success","contact", 'No New Contacts TO Import')
                if total_count:
                    self.all_contacts_imported_successfully = False
                    self.sh_total_customer = total_count
                    if total_count > 15000:
                        if self.cust_count == 0:
                            self.sh_total_half_customer = 10000
                        else:
                            self.sh_total_half_customer += 10000
                else:
                    raise UserError(_('Check Your Credentials and Try Again After Sometime'))
            self.recall_customer_data()

    def recall_customer_data(self):
        try:            
            headers = self.get_headers()
            if self.contact_import_between_dates:
                from_head = self.get_head(self.contact_from_date)
                to_head = self.get_head(self.contact_to_date)
                if not self.cust_last_count:
                    customer_url = "%s/admin/api/2021-07/customers.json?fields=id,first_name&limit=250&since_id=0&created_at_min=%s&created_at_max=%s" %(self.sh_host_name,from_head,to_head)
                else:
                    customer_url = "%s/admin/api/2021-07/customers.json?fields=id,first_name&limit=250&since_id=%s&created_at_min=%s&created_at_max=%s" %(self.sh_host_name,int(self.cust_last_count),from_head,to_head)
            elif not self.last_sync_contact:
                if not self.cust_last_count:
                    customer_url = "%s/admin/api/2021-07/customers.json?fields=id,first_name&limit=250&since_id=0" %(self.sh_host_name)
                else:
                    customer_url = "%s/admin/api/2021-07/customers.json?fields=id,first_name&limit=250&since_id=%s" %(self.sh_host_name,int(self.cust_last_count))
            else:
                head = self.get_head(self.last_sync_contact)
                if not self.cust_last_count:
                    customer_url = "%s/admin/api/2021-07/customers.json?fields=id,first_name&limit=250&since_id=0&updated_at_min=%s&created_at_min=%s" %(self.sh_host_name,head,head)
                else:
                    customer_url = "%s/admin/api/2021-07/customers.json?fields=id,first_name&limit=250&since_id=%s&updated_at_min=%s&created_at_min=%s" %(self.sh_host_name,int(self.cust_last_count),head,head)            
            response = requests.get(url=customer_url,headers=headers)            
            response_json = response.json()            
            if response.status_code == 200:            
                response_json = response.json()
                for data in response_json['customers']:
                    find_in_queue = False
                    domain = [('sh_contact_id', '=', data['id']),('queue_type', '=', 'contact')]                
                    find_in_queue = self.env['sh.queue'].search(domain)                    
                    if not find_in_queue:
                        queue_vals = {
                            'queue_type' : 'contact',    
                            'queue_sync_date' : datetime.now(),
                            'sh_contact_id' : data['id'],
                            'sh_current_state' : 'draft',
                            'sh_queue_name' : data['first_name']
                        }                    
                        self.env['sh.queue'].create(queue_vals)
                self.cust_last_count = 0            
                if response_json['customers']:
                    self.cust_count += 250
                    print("\n\n\n\n",self.cust_count)
                    self.cust_last_count = data['id']                   
                    if self.cust_count == self.sh_total_customer:
                        self.generate_vals("success","contact", 'Imported Successfully, Contacts added to the queue')
                        self.cust_count = 0
                        self.last_sync_contact = datetime.now()
                        self.cust_last_count = 0
                        self.sh_total_customer = False
                        self.sh_total_half_customer = 0
                        return
                    elif self.cust_count == self.sh_total_half_customer:
                        self.generate_vals("success","contact", 'Partially Imported, Import Again')
                        return
                    if len(response_json['customers']) == 250:
                        self.recall_customer_data()
                    else:
                        self.generate_vals("success","contact", 'Imported Successfully, Contacts added to the queue')
                        self.cust_count = 0
                        self.last_sync_contact = datetime.now()
                        self.cust_last_count = 0
                        self.sh_total_customer = False
                        self.sh_total_half_customer = 0
                elif len(response_json['customers']) == 0:
                    self.generate_vals("success","contact", 'No New Contacts TO Import')
                    return
                else:
                    self.generate_vals("error","contact", 'Failed, Something Went Wrong')
                    self.cust_last_count = 0
                    self.cust_count = 0
                    self.sh_total_customer = 0
                    self.sh_total_half_customer = 0
        except Exception as e:
            self.generate_vals("error","contact", e)

    def get_head(self,time):
        past = time
        past = past.isoformat()
        head, sep, tail = past.partition('.')
        head = head + '+00:00'
        return head
    def manually_from_queue(self,get_contacts):
        if get_contacts:
            contact_list = [data.sh_contact_id for data in get_contacts if data.queue_type == 'contact' and data.sh_contact_id]
            order_list = [data.sh_order_id for data in get_contacts if data.queue_type == 'order' and data.sh_order_id]    
            product_list = [data.sh_product_id for data in get_contacts if data.queue_type == 'product' and data.sh_product_id]
            from_where = 'force'
            if contact_list:
                rec = self.contact_import(contact_list,from_where)
                return rec
            if order_list:
                rec = self.sh_import_orders(order_list,from_where)
                return rec
            if product_list:
                rec = self.products_import(product_list,from_where)
                return rec

    def manage_import_contact(self):
        domain = []
        find_config = self.env['sh.shopify.configuration'].search(domain)
        for rec in find_config:
            if not rec.all_contacts_imported_successfully:            
                domain = [('queue_type', '=', 'contact'),('sh_current_state', '=', 'draft')]
                get_con = self.env['sh.queue'].search(domain,order = "id asc",limit=50)        
                import_list = []
                if get_con:
                    for data in get_con:
                        import_list.append(data.sh_contact_id) 
                    from_where = "normal"                        
                    find_config.contact_import(import_list,from_where)
                else:                    
                    rec.all_contacts_imported_successfully = True                    
                    rec.generate_vals("success","contact","Cron : Imported Successfully")
            
    def contact_import(self,import_list,from_where):
        try:
            headers = {
                'Content-Type' : 'application/json',
                'X-Shopify-Access-Token' : '%s' %(self.sh_password),
            }  
            check_count = 0
            for contactid in import_list:            
                check_count = check_count + 1                
                customer_url = "%s/admin/api/2021-07/customers/%s.json" %(self.sh_host_name,contactid)                
                response = requests.get(url=customer_url,headers=headers)
                response_json = response.json()
                valuesP = self.sort_created_contact(response)
                domain = [('sh_contact_id', '=', contactid),('queue_type', '=', 'contact')]
                get_that_contact = self.env['sh.queue'].search(domain)              
                if get_that_contact:
                    get_that_contact.unlink()
            if from_where == 'force' and valuesP:                
                self.generate_vals("success","contact","Imported Successfully")
                return self.show_popup_success()
            else:
                self.generate_vals("success","contact","Cron : Partially Imported")
        except Exception as e:
            self.generate_vals("error","contact",e)

    def sort_created_contact(self,response):        
        if response.status_code == 200:
            response_json = response.json()            
            if len(response_json['customer']) != 0:
                vals = {
                    'customer_rank' : 1,
                    'email' : response_json['customer']['email'] if response_json['customer']['email'] else False,
                    'phone' : response_json['customer']['phone'] if response_json['customer']['phone'] else False,
                    'comment' : response_json['customer']['note'] if response_json['customer']['note'] else False,
                }
                names = ''
                if response_json['customer']['first_name']:
                    if response_json['customer']['last_name']:
                        names = response_json['customer']['first_name'] + ' ' + response_json['customer']['last_name']
                        vals['shh_firstname'] = response_json['customer']['first_name']
                        vals['shh_lastname'] = response_json['customer']['last_name']
                    else:
                        names = response_json['customer']['first_name']
                        vals['shh_firstname'] = response_json['customer']['first_name']            
                elif response_json['customer']['last_name']:
                    names = response_json['customer']['last_name']
                    vals['shh_lastname'] = response_json['customer']['last_name']
                if names:
                    vals['name'] = names
                    if response_json['customer']['tags']:
                        tags = response_json['customer']['tags'].split(',')
                        for tag in tags:
                            domain = [('name', '=', tag)]
                            find_tag = self.env['res.partner.category'].search(domain)
                            if find_tag:
                                vals['category_id'] = find_tag.ids
                            else:
                                create_tag = self.env['res.partner.category'].create({'name':tag})                               
                                vals['category_id'] = create_tag.ids
                    if response_json['customer']['addresses']:
                        for value in response_json['customer']['addresses']:
                            vals = self.generate_address_vals(value,vals)
                    domain = [('sh_shopify_contact_id', '=', response_json['customer']['id'])]
                    find_contact = self.env['res.partner'].search(domain)               
                    if find_contact:
                        find_contact.write(vals)
                    else:
                        vals['sh_shopify_contact_id'] = response_json['customer']['id']
                        self.env['res.partner'].create(vals)                                       
                return True
            else:
                self.generate_vals("success","contact","No New Contacts To Import")
    
    def generate_address_vals(self,value,vals):
        vals['street'] = value['address1'] if value['address1'] else False
        vals['street2'] = value['address2'] if value['address2'] else False
        vals['city'] = value['city'] if value['city'] else False
        vals['zip'] = value['zip'] if value['zip'] else False
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

    def _shopify_contact_cron(self):
        domain = []
        find_config = self.env['sh.shopify.configuration'].search(domain)
        for data in find_config:
            if data.auto_import_contact:
                data.submit_contact()
        
    def reset_shopify_contact(self):
        self.last_sync_contact = False