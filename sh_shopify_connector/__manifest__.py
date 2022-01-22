# Part of Softhealer Technologies.
{
    "name": "Shopify-Odoo Connector",

    "author": "Softhealer Technologies",

    "website": "https://www.softhealer.com",

    "support": "support@softhealer.com",

    "version": "15.0.1",

    "license": "OPL-1",

    "category": "Sales",

    "summary": "Connect Shopify Store with Odoo manage Shopify store Contact shopify Contact Synchronization Shopify integration import images from shopify Contact From Shopify Odoo Shopify Product Integration shopify odoo bridge odoo Product Shopify Odoo",

    "description": """Using this app you can easily import products and contacts from shopify.""",

    "depends": ['contacts','stock','sale_management','sh_product_tags'],

    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/sh_shopify_creds.xml",
        "views/sh_shopify_contacts.xml",
        "views/sh_shopify_products.xml",
        "views/sh_shopify_draft_orders.xml",
        "views/sh_contact_queue.xml",
        "views/sh_order_queue.xml",
        "views/inherit_product_product.xml",
        "views/inherit_sale_order.xml",
        "views/popup_message.xml",
        'views/res_config_settings.xml' ,
        'views/auto_sale_workflow.xml',
        'views/sale_order.xml',
        'views/res_partner.xml',
        "views/sh_product_queue.xml",
    ],
    "images": ["static/description/background.png", ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "price": "100",
    "currency": "EUR"
}
