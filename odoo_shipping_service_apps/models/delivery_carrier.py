# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
from collections import defaultdict
from odoo import api, fields, models, _
import logging
from odoo.exceptions import Warning, UserError, ValidationError
from odoo.addons.odoo_shipping_service_apps.tools import DomainVals
BasicAddress = ['name', 'email', 'phone',
                'street', 'street2', 'city', 'zip', 'lang']

_logger = logging.getLogger(__name__)
DeliveryType = [
    ('fixed', 'Fixed Price'),
    ('base_on_rule', 'Based on Rules')
]
APIUoM = [
    ('LB', 'LB'),
    ('KG', 'KG'),
    ('OZ', 'OZ')
]


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    def _shipping_genrated_message(self, message):
        partial_id = self.env['wk.wizard.message'].create({'text': message})
        return {
            'name': "Shipping information!",
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'wk.wizard.message',
            'res_id': partial_id.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
        }

    def get_price_available(self, order):
        result = super(DeliveryCarrier, self).get_price_available(order)
        return result

    @api.model
    def wk_get_shipping_price_from_so(self, orders):
        for order in orders:
            if order.carrier_id.delivery_type not in ['fixed', 'base_on_rule']:
                if order.create_package == 'manual' and len(order.wk_packaging_ids) == 0:
                    raise ValidationError(
                        _('Create the package first for manual packaging of order %s.' % (order.name)))
        result = self.with_context(
            self._context).get_shipping_price_from_so(orders)[0]
        return result

    @api.model
    def wk_check_manual_package(self, orders):
        for order in orders:
            if order.carrier_id.delivery_type not in ['fixed', 'base_on_rule']:
                if order.create_package == 'manual' and len(order.wk_packaging_ids) == 0:
                    raise ValidationError(
                        _('Create the package first for manual packaging of order %s.' % (order.name)))
        return True

    @api.model
    def wk_check_carrier_bycontext(self, orders):
        domain = [
            ('delivery_type', 'not in', ['fixed', 'base_on_rule']),
            ('id', '!=', self.id)
        ]
        website_sale_delivery = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'website_sale_delivery'), ('state', '=', 'installed')]
        )
        if website_sale_delivery:
            domain += [('website_published', '=', True)]
        carriers = self.sudo().search(domain)
        return (self._context.get('website_id')
                and len(carriers) > 1
                and orders.carrier_id != self
                and (not self._context.get('wk_website')))

    def get_shipping_price_from_so(self, orders):

        # if self.wk_check_carrier_bycontext(orders=orders):
        #     _logger.info("wk_check_carrier_bycontext==%r====%r===="%(orders,self._context))
        # #
        #     return [0]
        # self.wk_check_manual_package(orders=orders)
        return super(DeliveryCarrier, self).get_shipping_price_from_so(orders)

    def _get_extra_price_source(self):
        return [('fixed', 'Fixed Amount'), ('percentage', '%  of Sale Order Amount')]

    _extra_price_source_selection = lambda self, * \
        args, **kwargs: self._get_extra_price_source(*args, **kwargs)

    image = fields.Binary(
        string='Website Image'
    )
    extra_price_source = fields.Selection(
        selection=_extra_price_source_selection,
        string='Extra Price Based On',
        default='fixed',
        required=True
    )
    extra_service_price = fields.Float(
        string='Extra Service Charges',
        help="Extra  Added Service Charge "
    )

    void_shipment = fields.Boolean(
        string='Void Shipment',
        help="Enable it if want 'Shipment Cancellation'",
        default=True
    )
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Odoo Product UoM',
        help='Shipping Equivalent UoM in Odoo'
    )
    delivery_uom = fields.Selection(
        selection=APIUoM,
        string='API UoM',
        help='Default UoM in Odoo'
    )
    packaging_id = fields.Many2one(
        comodel_name='product.packaging',
        string='Packaging'
    )
    default_product_weight = fields.Float(
        default=1,
        string='Default  Weight',
        help="Default  weight  will use in  package if product not have weight"
    )

    @api.model
    def _get_config(self, key='delivery.carrier'):
        return self.env[key].sudo().get_values()

    @api.model
    # Method called by Every Delivery Carrier wiht Fields as Argument ,which should a list for return their credentials as Dictionary.
    def wk_get_carrier_settings(self, Fields):
        return self.read(Fields)[0]

    @api.model
    def _get_default_uom(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        product_weight_in_lbs_param = get_param('product.weight_in_lbs')
        if product_weight_in_lbs_param == '1':
            return self.env.ref('uom.product_uom_lb')
        else:
            return self.env.ref('uom.product_uom_kgm')

    @api.model
    def wk_group_by(self, group_by, items):
        data = defaultdict(list)
        for item in items:
            data[item.get(group_by)].append(item)
        return data.items()

    @api.model
    def _get_weight(self, order=None, pickings=None):
        weight, volume, quantity = 0, 0, 0
        items = order.order_line if order else pickings.move_lines
        for line in items:
            if order and line.state == 'cancel':
                continue
            if order and (not line.product_id or line.is_delivery):
                continue
            q = self._get_default_uom()._compute_quantity(
                line.product_uom_qty, self.uom_id)
            weight += (line.product_id.weight or 0.0) * q
            volume += (line.product_id.volume or 0.0) * q
            quantity += q
        if not self._context.get('ignore_weight'):
            if not weight:
                raise ValidationError('ERROR {0}:\nProduct in {0} Must Have Weight For Getting Shipping Charges.'.format(
                    order and order.name or pickings.name))
        return weight

    @api.model
    def update_order_package(self, items, order):
        order.write(dict(wk_packaging_ids=[(5, 0)]))
        package_obj = self.env['product.package']
        wk_packaging_ids = []
        for item in items:
            item['order_id'] = order.id
            wk_packaging_ids.append(package_obj.create(item).id)
        order.write({'wk_packaging_ids': [(6, 0, wk_packaging_ids)]})
        return True

    @api.model
    def get_package_attribute(self, line, packaging_id, partial_package):
        product_qty, product_weight = 1, 1
        if not partial_package:
            product_id = line.product_id
            product_qty, product_weight = int(line.product_uom_qty) and int(
                line.product_uom_qty) or 1, product_id.weight and product_id.weight or 1
        else:
            product_weight = sum(map(lambda item: item.get('weight'), line))
        return product_qty, product_weight

    @api.model
    def wk_get_product_package(self, line, packaging_id, partial_package=None):
        """Return package count
            major package [package_count,capacity], minor package [package_count=1,capacity]

        """
        dimension = dict(height=packaging_id.package_type_id.height, width=packaging_id.package_type_id.width,
                         length=packaging_id.package_type_id.packaging_length, packaging_id=packaging_id.package_type_id.id)
        result = list()
        line_price = 0
        if partial_package:
            price_unit = sum(map(lambda item: item.get('price_unit', 0), line))
            if price_unit:
                line_price = price_unit/len(line)
        else:
            line_price = sum(map(lambda item: line.price_unit, line))/len(line)
        product_qty, product_weight = self.get_package_attribute(
            line, packaging_id, partial_package)
        max_qty, max_weight = int(packaging_id.qty) and int(
            packaging_id.qty) or 1, packaging_id.package_type_id.max_weight and packaging_id.package_type_id.max_weight or 1
        qty_capacity = int(max_weight//product_weight)
        if qty_capacity and qty_capacity < max_qty:
            # _logger.info("Condition-A -")
            package_count = product_qty//qty_capacity
            if package_count:
                # _logger.info("Condition-A1 -")
                multi_pckg_qty_capacity = dimension.copy()
                multi_pckg_qty_capacity.update(dict(
                    weight=product_weight*qty_capacity,
                    full_capacity=True,
                    wk_cover_amount=line_price*qty_capacity,
                ))

                result += [multi_pckg_qty_capacity]*package_count

            if product_qty % qty_capacity:
                # _logger.info("Condition-A2 -")
                single_pckg_qty_capacity = dimension.copy()
                single_pckg_qty_capacity.update(dict(
                    weight=product_weight*(product_qty % qty_capacity),
                    full_capacity=False,
                    wk_cover_amount=line_price*(product_qty % qty_capacity),
                ))
                result += [single_pckg_qty_capacity]*1

        else:
            # _logger.info("-Condition-B---")
            package_count = product_qty//max_qty
            if package_count:
                # _logger.info("-Condition-B1---")

                multi_pckg_max_qty = dimension.copy()
                multi_pckg_max_qty.update(dict(
                    weight=product_weight*max_qty,
                    full_capacity=True,
                    wk_cover_amount=line_price*max_qty,
                ))
                _logger.info("-Condition-B1-%r--%r==%r====%r" %
                             ([multi_pckg_max_qty], package_count, product_qty, max_qty))
                result += [multi_pckg_max_qty]*package_count
            if product_qty % max_qty:
                # _logger.info("-Condition-B2---")
                single_pckg_max_qty = dimension.copy()
                single_pckg_max_qty.update(dict(
                    weight=product_weight*(product_qty % max_qty),
                    full_capacity=False,
                    wk_cover_amount=line_price*(product_qty % max_qty),
                ))
                result += [single_pckg_max_qty]*1

        return result

    @api.model
    def wk_validate_data(self, order=None, pickings=None):
        if pickings:
            if not pickings.package_ids:
                raise ValidationError(
                    'Create the package before sending to shipper.')
            else:
                package_ids = pickings.package_ids.filtered(
                    lambda package_id: not package_id.package_type_id)
                if len(package_ids):
                    raise ValidationError('Packaging is not set for package %s.' % (
                        ','.join(package_ids.mapped('name'))))

    @api.model
    def wk_get_packaging_id(self, product_id=None, package_id=None):
        pck_id = self.packaging_id
        packaging_id = None
        if product_id:
            packaging_ids = product_id.wk_packaging_ids.filtered(
                lambda pck_id: pck_id.package_carrier_type == self.delivery_type)
            packaging_id = packaging_ids and packaging_ids[0] or pck_id
        elif package_id:
            packaging_id = package_id.package_type_id or pck_id

        if packaging_id:
            return packaging_id
        raise ValidationError(
            'Packaging is not set of product and carrier %s as well.' % (self.name))

    @api.model
    def wk_group_by_packaging(self, order=None, pickings=None):
        packagings = defaultdict(list)
        if order:
            for line in order.order_line:
                if line.state == 'cancel':
                    continue
                product_id = line.product_id
                if (not product_id or line.is_delivery):
                    continue
                packaging_id = self.wk_get_packaging_id(product_id=product_id)
                packagings[packaging_id].append(line)

        else:
            for package_id in pickings.package_ids:
                packaging_id = self.wk_get_packaging_id(package_id=package_id)
                packagings[packaging_id].append(package_id)

        return dict(packagings.items())

    @api.model
    def wk_merge_half_package(self, items):
        data = defaultdict(list)
        for item in filter(lambda item: not item.get('full_capacity'), items):
            packaging_id = item.get('packaging_id')
            if type(packaging_id) == int:
                packaging_id = self.env['product.packaging'].browse(
                    packaging_id)
            data[packaging_id].append(item)
        new_dict = dict()
        for key, value in data.items():
            if len(value) > 1:
                new_dict[key] = value
                for val in value:
                    items.remove(val)
        # _logger.info("new_dict-packagings--%r-----",new_dict)
        for packaging_id, lines in new_dict.items():
            items.extend(self.wk_get_product_package(
                lines, packaging_id, partial_package=True))
        return items

    @api.model
    def wk_get_order_package(self, order):
        result = []
        if order.create_package == 'auto':
            packagings = self.wk_group_by_packaging(order)
            for packaging_id, lines in packagings.items():
                for line in lines:
                    result.extend(
                        self.wk_get_product_package(line, packaging_id))
            result = self.wk_merge_half_package(result)
            # if order.carrier_id==self:
            #     self.update_order_package(result,order)
        else:
            return map(lambda wk_packaging_id: dict(
                packaging_id=wk_packaging_id.packaging_id.id,
                weight=wk_packaging_id.weight,
                width=wk_packaging_id.width,
                length=wk_packaging_id.length,
                height=wk_packaging_id.height
            ), order.wk_packaging_ids)

        return result

    @api.model
    def get_package_count(self, weight_limit, order=None, pickings=None):
        WeightValue = self._get_weight(
            order=order) if order else self._get_weight(pickings=pickings)
        assert (WeightValue != 0.0), _(
            'Product in Order Must Have Weight For Getting Shipping Charges.')
        last_package = WeightValue % weight_limit
        total_package = int(WeightValue // weight_limit)
        return WeightValue, weight_limit, last_package, total_package + int(bool(last_package))

    @api.model
    def _get_api_weight(self, shipping_weight):
        q = self._get_default_uom()._compute_quantity(
            1, self.uom_id)
        weight = (shipping_weight or 0.0) * q
        return weight

    @api.model
    def _get_per_order_line_weight(self, line):
        return (line.product_id.weight or 0.0) * self._get_default_uom()._compute_quantity(line.product_uom_qty, self.uom_id)

    @api.model
    def convert_shipment_price(self, data):
        price = data.get('price')
        actual_price = price
        currency_id = data.get('currency_id')
        currency = data.get('currency')
        if currency_id and currency:
            if currency_id.name != currency:
                currency = currency_id.search(
                    [('name', '=', currency)], limit=1)
                actual_price = currency.compute(price, currency_id)
        return actual_price

    def get_shipment_currency_id(self, order=None, pickings=None):
        currency = None  # ,'USD'
        if order:
            currency = order.currency_id
        elif pickings:
            if pickings.sale_id and pickings.sale_id.currency_id:
                currency = pickings.sale_id.currency_id
            else:
                currency = pickings.company_id.currency_id
                if not currency:
                    warehouse = pickings.picking_type_id and pickings.picking_type_id.warehouse_id
                    if warehouse:
                        currency = (warehouse.property_product_pricelist
                                    and warehouse.property_product_pricelist.currency_id)
        if not currency:
            currency = currency or self.env['res.currency'].search(
                ('name', 'in', ['USD', 'EUR']), limit=1)
        return currency

    def get_shipment_currency(self, order=None, pickings=None):
        currency = 'USD'
        if order:
            currency = order.currency_id.name
        elif pickings:
            if pickings.sale_id.currency_id:
                currency = pickings.sale_id.currency_id.name
            else:
                currency = pickings.company_id.currency_id.name
        return currency

    def _get_shipment_address(self, data, entity):
        if data and not data.get('company_name') and hasattr(entity, 'company_name') and entity.company_name:
            data['company_name'] = entity.company_name
        return data

    def get_shipment_address(self, entity):
        data = entity.read(BasicAddress)[0]
        company_name = None
        if entity.parent_id:
            company_name = entity.parent_id.name

        data['country_name'] = entity.country_id.name
        data['country_code'] = entity.country_id.code
        data['state_name'] = entity.state_id.name
        data['state_code'] = entity.state_id.code
        data['company_name'] = company_name
        data = self._get_shipment_address(data, entity)
        return data

    def get_shipment_recipient_address(self, order=None, picking=None):
        if order:
            recipient = order.partner_shipping_id if order.partner_shipping_id else order.partner_id
        else:
            recipient = picking.partner_id
        if not len(recipient):
            raise ValidationError('Please check partner address.')
        return self.get_shipment_address(recipient)

    def get_shipment_shipper_address(self, order=None, picking=None):
        if order:
            shipper = order.warehouse_id.partner_id
        else:
            shipper = picking.picking_type_id.warehouse_id.partner_id
        if not len(shipper):
            raise ValidationError('Please check warehouse address.')
        return self.get_shipment_address(shipper)

    @api.model
    def wk_get_history_hash(self,  order, partner, **kwargs):
        match = True
        History = self.env['delivery.carrier.history']
        zip_code = partner.zip
        state_code = partner.state_id and partner.state_id.code or ''
        country_code = partner.country_id and partner.country_id.code or ''

        domain = History.wk_generate_hash_domain(
            carrier_id=self,
            order=order,
            partner=partner.id,
            zip_code=zip_code,
            state_code=state_code,
            country_code=country_code,
            currency=self.get_shipment_currency(order=order)
        )
        history = History.search(domain)
        if not history:
            match = False
            vals = DomainVals(domain)
            vals.update(
                dict(
                    order_id=order.id,
                    carrier_id=self.id,
                    zip_code=zip_code,
                    state_code=state_code,
                    country_code=country_code,
                )
            )
            history = History.create(vals)
        return dict(
            history=history,
            match=match,
        )
