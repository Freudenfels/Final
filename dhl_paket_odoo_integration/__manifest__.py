# -*- coding: utf-8 -*-pack
{
    # App information
    'name': 'DHL Paket(Business Customer API) Shipping Integrations',
    'category': 'Website',
    'version': '15.17.12.2021',
    'summary': """Using DHL Paket(Business Customer API) Shipping Integrations we connect with DHL Paket(Business Customer API). using DHL Paket(Business Customer API) Shipping Integrations we generate the label.""",
    'description': """
       Using DHL Paket(Business Customer API) Shipping Integrations we connect with DHL Paket(Business Customer API). using DHL Paket(Business Customer API) Shipping Integrations we generate the label.We also Provide the dhl,bigcommerce,shiphero,gls,fedex,usps,easyship,stamp.com,dpd,shipstation,manifest report.
""",

    # Dependencies
    'depends': ['delivery'],
    # Views
    'data': ['views/delivery_carrier.xml',
        'views/res_company.xml'],

    # Author
    'author': 'Vraja Technologies',
    'website': 'http://www.vrajatechnologies.com',
    'maintainer': 'Vraja Technologies',
    'live_test_url': 'http://www.vrajatechnologies.com/contactus',
    'images': ['static/description/cover.jpg'],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': '99',
    'currency': 'EUR',
    'license': 'OPL-1',

}