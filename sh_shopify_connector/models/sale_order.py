# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models,_,api
from odoo.exceptions import UserError, ValidationError


MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'out_receipt': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'in_receipt': 'supplier',
}

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    workflow_id = fields.Many2one('sh.auto.sale.workflow',string = "Sale Workflow")
    is_boolean = fields.Boolean(related = "company_id.group_auto_sale_workflow")

    @api.onchange('partner_id')
    def get_workflow(self):
        if self.partner_id.workflow_id:
            if self.company_id.group_auto_sale_workflow:
                self.workflow_id = self.partner_id.workflow_id
        else:
            if self.company_id.group_auto_sale_workflow and self.company_id.workflow_id:
                self.workflow_id = self.company_id.workflow_id

    def action_confirm(self):
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write({
            'state': 'sale',
            # 'date_order': fields.Datetime.now()
        })

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()

        # return True
        if self.workflow_id:
            if self.workflow_id.validate_order and self.picking_ids:
                if self.workflow_id.force_transfer:
                    for picking in self.picking_ids:
                        for stock_move in picking.move_ids_without_package:
                            if stock_move.move_line_ids:
                                stock_move.move_line_ids.update({
                                    'qty_done':stock_move.product_uom_qty,
                                })
                            else:
                                self.env['stock.move.line'].create({
                                    'picking_id':picking.id,
                                    'move_id':stock_move.id,
                                    'date':stock_move.date,
                                    'reference':stock_move.reference,
                                    'origin':stock_move.origin,
                                    'qty_done':stock_move.product_uom_qty,
                                    'product_id':stock_move.product_id.id,
                                    'product_uom_id':stock_move.product_uom.id,
                                    'location_id':stock_move.location_id.id,
                                    'location_dest_id':stock_move.location_dest_id.id
                                })
                        picking.button_validate()
                        if picking.state != 'done':
                            sms = self.env['confirm.stock.sms'].create({ 
                                'picking_id': picking.id,
                            })
                            sms.send_sms()
                            
                else:
                    for picking in self.picking_ids:
                        picking.button_validate()

                        wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]})
                        wiz.process()

                        if picking.state != 'done':
                            sms = self.env['confirm.stock.sms'].create({ 
                                'picking_id': picking.id,
                            })
                            sms.send_sms()
                            ret = picking.button_validate()
                            if 'res_model' in ret and ret['res_model'] == 'stock.backorder.confirmation':
                                backorder_wizard = self.env['stock.backorder.confirmation'].create({
                                    'pick_ids':[(4,picking.id)]
                                })
                                backorder_wizard.process()                    
                    
            if self.workflow_id.create_invoice:
                invoice = self._create_invoices()
                if  self.workflow_id.sale_journal:
                    invoice.write({
                        'journal_id' : self.workflow_id.sale_journal.id
                    })
                
                if self.workflow_id.validate_invoice:
                    invoice.action_post()

                    if self.workflow_id.send_invoice_by_email:
                        template_id = self.env.ref('account.email_template_edi_invoice')
                        template_id.with_context(model_description='').sudo().send_mail(invoice.id, force_send=True,notif_layout="mail.mail_notification_paynow")

                    if self.workflow_id.register_payment:
                        
                        # payment_methods = self.env['account.payment.method'].search([('payment_type','=','inbound')])
                        # journal = self.env['account.journal'].search([('type','in',('bank','cash'))])
                        payment = self.env['account.payment'].create({
                            'currency_id': invoice.currency_id.id,
                            'amount':invoice.amount_total,
                            'payment_type': 'inbound',
                            'partner_id': invoice.commercial_partner_id.id,
                            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.type],
                            'communication': invoice.invoice_payment_ref or invoice.ref or invoice.name,
                            'invoice_ids': [(6, 0, invoice.ids)],
                            'payment_method_id':self.workflow_id.payment_method.id,
                            'journal_id':self.workflow_id.payment_journal.id,
                            'payment_date':invoice.invoice_date
                        })
                    
                        payment.post()


    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        # ensure a correct context for the _get_default_journal method and company-dependent fields
        self = self.with_context(default_company_id=self.company_id.id, force_company=self.company_id.id)
        journal = self.env['account.move'].with_context(default_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))

        invoice_vals = {
            'ref': self.client_order_ref or '',
            'type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'user_id': self.user_id.id,
            'invoice_user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'invoice_partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_payment_ref': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'invoice_date':self.date_order.date(),
        }
        return invoice_vals

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_invoice_values(self, order, name, amount, so_line):
        invoice_vals = {
            'ref': order.client_order_ref,
            'type': 'out_invoice',
            'invoice_origin': order.name,
            'invoice_user_id': order.user_id.id,
            'narration': order.note,
            'partner_id': order.partner_invoice_id.id,
            'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
            'partner_shipping_id': order.partner_shipping_id.id,
            'currency_id': order.pricelist_id.currency_id.id,
            'invoice_payment_ref': order.reference,
            'invoice_payment_term_id': order.payment_term_id.id,
            'invoice_partner_bank_id': order.company_id.partner_id.bank_ids[:1].id,
            'team_id': order.team_id.id,
            'campaign_id': order.campaign_id.id,
            'medium_id': order.medium_id.id,
            'source_id': order.source_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': name,
                'price_unit': amount,
                'quantity': 1.0,
                'product_id': self.product_id.id,
                'product_uom_id': so_line.product_uom.id,
                'tax_ids': [(6, 0, so_line.tax_id.ids)],
                'sale_line_ids': [(6, 0, [so_line.id])],
                'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                'analytic_account_id': order.analytic_account_id.id or False,
            })],
            'invoice_date':order.date_order.date(),
        }

        return invoice_vals