# -*- coding: utf-8 -*-
##############################################################################
#
#    ODOO, Open Source Management Solution
#    Copyright (C) 2016 - 2020 Steigend IT Solutions (Omal Bastin)
#    Copyright (C) 2020 - Today O4ODOO (Omal Bastin)
#    For more details, check COPYRIGHT and LICENSE files
#
##############################################################################

{
    'name': "DHL Paket / Business Customer Shipping Api Integration",
    'summary':"DHL Paket / Business Customer Shipping Api Integration for Germany and Austria",
    'description': """
DHL Paket / Business Customer Shipping Api Integration Integration for Germany and Austria
==========================================================================================
Send your shippings through DHL Business customer API or DHL Paket and track them online. 
After installing this module you will be able to see new delivery method called 'DHL DE Paket'. 
Create a new delivery method with delivery type as 'DHL DE Paket' and specify the 
    * Username
    * Password
    * Account Number
    * Application ID 
    * Signature
    * Partner Number and
    * Product code

    -For testing purpose, you will have to provide the developer ID and password of your developer account instead of intraship username and password.
Specify the delivery method in Sale Or Delivery Order so that when transfering the product it will automatically pull the tracking reference 
and the label url to print the label created under the DHL Intraship which gives the ability to print the label directly from ODOO. 

It also manages the DHL Poststation address(Germany).


Transit insurance and cash on delivery feature not implemented.

For any support contact o4odoo@gmail.com or omalbastin@gmail.com
    """,
    'author': "Omal Bastin / O4ODOO",
    'license': 'OPL-1',
    'website': "https://o4odoo.com",
    'category': 'Technical Settings',
    'version': '15.0.1.0.2',
    'depends': ['delivery', 'mail'],
    'data': [
        'views/delivery_dhl_view.xml',
        'data/delivery_dhl_de_paket_data.xml'
    ],
    'application':True,
    'currency': 'EUR',
    'price': '125.0',
    'external_dependencies': {'python': ['suds-community' #sudo pip3 install suds-community
                                      ],
                           },
    'images': ['static/description/dhl-banner.png'],
    'demo': [
    ],
    'installable': True,
    # 'uninstall_hook': 'uninstall_hook',
    
    
}
