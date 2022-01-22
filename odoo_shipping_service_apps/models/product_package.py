# -*- coding: utf-8 -*-
#################################################################################
# Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
import logging
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)
Delivery = [
    ('none', 'None'),
    ('fixed', 'Fixed'),
    ('base_on_rule', 'Base on Rule'),
    # ('fedex','fedex'),
    # ('ups','ups'),
    # ('usps','USPS'),
    # ('auspost','auspost'),
]


class product_package_line(models.Model):
    _name = "product.package.line"
    _description = "Product Package Line"

    @api.onchange('order_id')
    def onchage_order_id(self):
        return {'domain': {
            'product_id': [('id', 'in', self.order_id.order_line.mapped('product_id.id'))]
        }
        }

    @api.onchange('product_id')
    def onchage_product_id(self):
        default_product_weight = 0
        order_id = self.order_id
        if order_id:
            default_product_weight = order_id.carrier_id.default_product_weight
        self.weight = self.product_id.weight or default_product_weight

    order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Order Line'
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
    )
    weight = fields.Float(
        default=0,
    )
    qty = fields.Float(
        default=1,
    )
    product_package_id = fields.Many2one(
        comodel_name='product.package',
        string='Package'
    )
    order_id = fields.Many2one(
        related='product_package_id.order_id',
    )


class product_package(models.Model):
    _name = "product.package"
    _description = "Product Package"

    @api.model
    def default_get(self, fields=None):
        res = super(product_package, self).default_get(fields)
        if self._context.get('wk_sale_id'):
            res['order_id'] = self._context.get('wk_sale_id')
        return res

    @api.depends('order_id', 'packaging_id')
    def _complete_name(self):
        for obj in self:
            name = obj.picking_id.name
            if obj.order_id:
                name = obj.order_id.name + "[%s]" % (name)
            obj.complete_name = name

    @api.depends('package_line_ids')
    def _compute_qty_weight_cover_amount(self):
        for rec in self:
            package_line_ids = rec.package_line_ids
            default_product_weight = rec.carrier_id.default_product_weight
            packaging_id = rec.packaging_id
            cover_amount, qty, weight = 0, 0, 0
            for line_id in package_line_ids:
                lqty = line_id.qty
                qty += lqty
                order_line_id = line_id.order_line_id
                if order_line_id:
                    product_id = order_line_id.product_id
                    cover_amount += packaging_id.get_cover_amount(
                        order_line_id.price_unit*lqty) or 0
                    if product_id:
                        weight += (line_id.weight or default_product_weight)*lqty
            rec.cover_amount = cover_amount
            rec.weight = weight
            rec.qty = qty

    @api.onchange('packaging_id')
    def _onchange_packaging_id(self):
        packaging_id = self.packaging_id
        if packaging_id:
            packaging_data = packaging_id.read(
                ['width', 'height', 'packaging_length'])[0]
            self.width = packaging_data.get('width')
            self.length = packaging_data.get('packaging_length')
            self.height = packaging_data.get('height')

    @api.model
    def _default_uom(self):
        uom_categ_id = self.env.ref('uom.product_uom_categ_kgm').id
        return self.env['uom.uom'].search([('category_id', '=', uom_categ_id), ('factor', '=', 1)], limit=1)

    complete_name = fields.Char(
        compute=_complete_name,
        string="Package Name",
    )
    packaging_id = fields.Many2one(
        comodel_name='stock.package.type',
        string='Packaging',
        required=True
    )
    order_id = fields.Many2one(
        comodel_name='sale.order'
    )
    carrier_id = fields.Many2one(
        related='order_id.carrier_id'
    )
    delivery_type = fields.Selection(
        selection=Delivery
    )
    full_capacity = fields.Boolean(

    )
    cover_amount = fields.Float(
        string='Cover Amount',
        default=0,
        # compute = _compute_qty_weight_cover_amount
    )
    qty = fields.Float(
        default=0,
        # compute = _compute_qty_weight_cover_amount
    )
    weight = fields.Float(
        string='Weight(kg)',
        default=0,
        # compute = _compute_qty_weight_cover_amount
    )
    height = fields.Integer(
        default=1
    )
    width = fields.Integer(
        default=1
    )
    length = fields.Integer(
        default=1
    )

    weight_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        readonly=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for Weight",
        default=lambda self: self._default_uom
    )
    package_line_ids = fields.One2many(
        'product.package.line',
        'product_package_id',
        string='Package Line'
    )
