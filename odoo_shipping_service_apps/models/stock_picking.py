# -*- coding: utf-8 -*-
#################################################################################
# Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def get_picking_price(self, package_id):
        move_line_ids = self.env['stock.move.line'].search(
            [('result_package_id', '=', package_id.id)])
        return sum([x.qty_done * x.product_id.list_price for x in move_line_ids])

    @api.model
    def wk_update_package(self, package_id=None):
        if self.carrier_id.delivery_type not in ['base_on_rule', 'fixed']:
            packaging_id = package_id.packaging_id
            if package_id and (not packaging_id):
                packaging_id = self.carrier_id.packaging_id
                package_id.packaging_id = packaging_id.id
            amount = self.get_picking_price(package_id)
            package_id.cover_amount = packaging_id.get_cover_amount(amount)
        return True

    def action_put_in_pack(self):
        self.ensure_one()
        cover = 0
        carrier_id = self.carrier_id
        move_line_ids = [
            po for po in self.move_line_ids if po.qty_done > 0 and not po.result_package_id]
        total_weight = sum(
            [po.qty_done * po.product_id.weight for po in move_line_ids])

        if carrier_id.packaging_id.package_type_id.cover_amount_option == 'fixed':
            cover = self.carrier_id.packaging_id.package_type_id.cover_amount
        else:
            cover_amount = sum(
                [po.qty_done * po.product_id.lst_price for po in move_line_ids])
            cover = cover_amount

        if total_weight == 0:
            shipping_weight = self.carrier_id.default_product_weight
        else:
            shipping_weight = total_weight

        res = super(StockPicking, self).action_put_in_pack()
        if res and (type(res) == dict):
            context = res.get('context') and res.get(
                'context').copy() or dict()
            delivery_type = context.get('current_package_carrier_type')
            ctx = {
                'no_description':
                not(delivery_type in ['fedex', 'dhl',
                    'ups', 'auspost', 'canada_post']),
                'no_cover_amount':
                    not(delivery_type in [
                        'fedex', 'dhl', 'ups', 'usps', 'auspost', 'canada_post']),
                'no_edt_document':
                    not(delivery_type in ['fedex', 'ups']),
                'current_package_picking_id': self.id,

            }

            if carrier_id and carrier_id.delivery_type not in ['base_on_rule', 'fixed']:
                ctx['default_delivery_packaging_id'] = self.carrier_id.packaging_id.package_type_id.id
                ctx['default_height'] = self.carrier_id.packaging_id.package_type_id.height
                ctx['default_width'] = self.carrier_id.packaging_id.package_type_id.width
                ctx['default_length'] = self.carrier_id.packaging_id.package_type_id.packaging_length
                ctx['default_cover_amount'] = cover
                ctx['default_shipping_weight'] = shipping_weight
            context.update(ctx)
            res['context'].update(context)

            """
            Extra code for creating with default values beacuse now wizard is not created with default values
            """
            """
            If any error came in package or picking please check the feilds of wizard and add the remaining feilds with value if any
            """
            vals = dict(
                delivery_package_type_id=self.carrier_id.packaging_id.package_type_id.id,
                height=self.carrier_id.packaging_id.package_type_id.height,
                width=self.carrier_id.packaging_id.package_type_id.width,
                wkk_length=self.carrier_id.packaging_id.package_type_id.packaging_length,
                cover_amount=cover,
                shipping_weight=shipping_weight,
                picking_id=res['context']['default_picking_id'],
            )
            wiz = self.env['choose.delivery.package'].sudo().create(vals)
            wiz.onchange_delivery_packaging_id()
            res['res_id'] = wiz.id
        return res

    @api.depends('package_ids')
    def _compute_cover_amount(self):
        for obj in self:
            obj.cover_amount = sum(obj.package_ids.mapped('cover_amount'))

    label_genrated = fields.Boolean(string='Label Generated', copy=False)
    shipment_uom_id = fields.Many2one(related='carrier_id.uom_id', readonly="1",
                                      help="Unit of measurement for use by Delivery method", copy=False)

    date_delivery = fields.Date(string='Expected Date Of Delivery',
                                help='Expected Date Of Delivery :The delivery time stamp provided by Shipment Service', copy=False, readonly=1)
    weight_shipment = fields.Float(
        string='Send Weight', copy=False, readonly=1)
    cover_amount = fields.Float(
        string='Cover Amount',
        compute='_compute_cover_amount',
        copy=False, readonly=1)

    def action_cancel(self):
        for obj in self:
            if obj.label_genrated == True:
                raise ValidationError(
                    'Please cancel the shipment before canceling  picking! ')
        return super(StockPicking, self).action_cancel()

    def do_new_transfer(self):
        for pick in self:
            carrier_id = pick.carrier_id
            if carrier_id and (carrier_id.delivery_type not in ['base_on_rule', 'fixed']):
                if not len(pick.package_ids):
                    raise ValidationError(
                        'Create the package first for picking %s before sending to shipper.' % (pick.name))
        return super(StockPicking, self).do_new_transfer()

    def send_to_shipper(self):
        _logger.info(
            "=============$$$$ STATE STATE  $$$$===============%s", self.state)
        self.ensure_one()
        if self.carrier_id.delivery_type and (self.carrier_id.delivery_type not in ['base_on_rule', 'fixed']):
            if not len(self.package_ids):
                raise ValidationError(
                    'Create the package first for picking %s before sending to shipper.' % (self.name))
            else:
                # try:
                res = self.carrier_id.send_shipping(self)
                self.carrier_price = res.get('exact_price')
                self.carrier_tracking_ref = res.get(
                    'tracking_number') and res.get('tracking_number').strip(',')
                self.label_genrated = True
                self.date_delivery = res.get('date_delivery')
                self.weight_shipment = float(res.get('weight'))
                msg = _("Shipment sent to carrier %s for expedition with tracking number %s") % (
                    self.carrier_id.delivery_type, self.carrier_tracking_ref)
                self.message_post(
                    body=msg,
                    subject="Attachments of tracking",
                    attachments=res.get('attachments')
                )
                # except Exception as e:
                #     return self.carrier_id._shipping_genrated_message(e)

    @api.model
    def unset_fields_prev(self):
        self.carrier_tracking_ref = False
        self.carrier_price = False
        self.label_genrated = False
        self.date_delivery = False
        self.weight_shipment = False
        # self.number_of_packages = False
        return True

    def cancel_shipment(self):
        self.ensure_one()
        # try:
        if self.carrier_id.void_shipment:
            self.carrier_id.cancel_shipment(self)
            msg = "Shipment of  %s  has been canceled" % self.carrier_tracking_ref
            self.message_post(body=msg)
            self.unset_fields_prev()

        else:
            msg = 'Void Shipment not allowed, please contact your Admin to enable the  Void Shipment for %s.' % (
                self.carrier_id.name)
            self.message_post(
                body=msg, subject="Not allowed to Void the Shipment.")
            return self.carrier_id._shipping_genrated_message(msg)
        # except Exception as e:
        #     return self.carrier_id._shipping_genrated_message(e)
