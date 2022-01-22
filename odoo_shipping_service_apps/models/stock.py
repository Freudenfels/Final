# -*- coding: utf-8 -*-
#################################################################################
# Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
from collections import Counter
from datetime import datetime, timedelta
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)
Delivery = [
    ('none', 'None'),
    ('fixed', 'Fixed'),
    ('base_on_rule', 'Base on Rule'),
    ('fedex', 'fedex'),
    ('ups', 'ups'),
    ('usps', 'USPS'),
    ('auspost', 'auspost'),

]
AmountOption = [
    ('fixed', 'Fixed Amount'),
    ('percentage', '%  of Product Price')
]


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def manage_package_type(self):
        self.ensure_one()
        res = super(StockMoveLine, self).manage_package_type()
        if res and (type(res) == dict):
            delivery_type = self.picking_id.carrier_id.delivery_type not in [
                'base_on_rule', 'fixed'] and self.picking_id.carrier_id.delivery_type or 'none'
            context = res.get('context') and res.get(
                'context').copy() or dict()
            ctx = {
                'no_description':
                not(delivery_type in [
                    'fedex', 'dhl', 'ups', 'auspost', 'canada_post'] and delivery_type or False),
                'no_cover_amount':
                not(delivery_type in ['fedex', 'dhl', 'ups', 'usps',
                    'auspost', 'canada_post'] and delivery_type or False),
                'no_edt_document':
                    not(delivery_type in ['fedex', 'ups']
                        and delivery_type or False),
                'current_package_picking_id': self.picking_id.id,
            }
            context.update(ctx)
            res['context'] = context
            self.picking_id.wk_update_package(self.result_package_id)
        return res


class ChooseDeliveryPackage(models.TransientModel):
    _inherit = "choose.delivery.package"

    height = fields.Integer(
        string='Height'
    )
    width = fields.Integer(
        string='Width'
    )
    wkk_length = fields.Integer(
        string='Length'
    )
    cover_amount = fields.Integer(
        string='Cover Amount',
        help='This is the declared value/cover amount for an individual package.'
    )
    description = fields.Text(
        string='Description',
        help='The text describing the package.'
    )
    order_id = fields.Many2one(
        comodel_name='sale.order'
    )
    _sql_constraints = [
        ('positive_cover_amount', 'CHECK(cover_amount>=0)',
         'Cover Amount must be positive (cover_amount>=0).'),
        ('positive_shipping_weight', 'CHECK(shipping_weight>=0)',
         'Shipment weight must be positive (shipping_weight>=0).'),

    ]

    # @api.onchange('delivery_packaging_id')              Commented till default fields are not created.
    @api.onchange('delivery_package_type_id')
    def onchange_delivery_packaging_id(self):
        packaging_id = self.delivery_package_type_id
        _logger.info("--------------- called %r--------------" %
                     self.delivery_package_type_id)

        if packaging_id:
            self.height = packaging_id.height
            self.width = packaging_id.width
            self.wkk_length = packaging_id.packaging_length
            self.cover_amount = packaging_id.get_cover_amount(
                self.cover_amount)
            _logger.info("===%r====%r====+%r====%r" %
                         (self.height, self.width, self.wkk_length, self.cover_amount))

    def get_shipping_fields(self):
        return ['height', 'width', 'length', 'cover_amount', 'description']

    def update_shipping_package(self, stock_quant_package_id):
        data = self.read(self.get_shipping_fields())[0]
        data.pop('id')
        stock_quant_package_id.write(data)
        return True

    def action_put_in_pack(self):
        packaging_id = self.delivery_package_type_id
        if packaging_id and (packaging_id.package_carrier_type not in ['none']):
            if packaging_id and (packaging_id.max_weight < self.shipping_weight):
                msz = _('Shipment weight should be less then {max_weight} kg  as {max_weight} kg is the max weight limit set  for {name}  .'.format(
                    max_weight=packaging_id.max_weight, name=packaging_id.name))
                _logger.info("Weight Check: %s  ", msz)
                raise ValidationError(msz)

        ctx = dict(self._context)
        ctx['default_cover_amount'] = self.cover_amount
        ctx['default_shipping_weight'] = self.shipping_weight
        ctx['default_height'] = self.height
        ctx['default_width'] = self.width
        ctx['default_length'] = self.wkk_length
        super(ChooseDeliveryPackage, self.with_context(ctx)).action_put_in_pack()


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"
    package_carrier_type = fields.Selection(
        related='package_type_id.package_carrier_type')
    height = fields.Integer(string='Height')
    width = fields.Integer(string='Width')
    length = fields.Integer(string='Length')
    cover_amount = fields.Integer(
        string='Cover Amount', help='This is the declared value/cover amount for an individual package.')
    description = fields.Text(string='Description',
                              help='The text describing the package.')

    order_id = fields.Many2one(comodel_name='sale.order')
