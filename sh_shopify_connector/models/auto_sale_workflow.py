from odoo import fields, models

class AutoSaleWorkflow(models.Model):
    _name = 'sh.auto.sale.workflow'
    _description = "Auto Workflow Working"

    name = fields.Char(string = "Name",required= True)
    validate_order = fields.Boolean(string = "Validate Delivery Order")
    create_invoice = fields.Boolean(string = "Create Invoice")
    validate_invoice = fields.Boolean(string = "Validate Invoice")
    register_payment = fields.Boolean(string = "Register Payment")
    send_invoice_by_email = fields.Boolean(string = "Send Invoice By Email")
    sale_journal = fields.Many2one('account.journal',string = "Sale Journal",)
    payment_journal = fields.Many2one('account.journal',string = "Payment Journal",)
    payment_method = fields.Many2one('account.payment.method',string = "Payment Method")
    force_transfer = fields.Boolean(string = "Force Transfer")

