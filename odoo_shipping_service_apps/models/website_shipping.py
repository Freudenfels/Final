# -*- coding: utf-8 -*-
#################################################################################
# Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
from hashlib import sha256
import hmac
from odoo import api, fields, models


class DeliveryCarrierHistory(models.Model):
    _name = "delivery.carrier.history"
    _description = "Carrier History"
    _rec_name = 'order_id'

    order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Order'
    )
    carrier_id = fields.Many2one(
        comodel_name='delivery.carrier',
        string='Carrier'
    )
    price = fields.Float(
        string="Price"
    )
    currency = fields.Char(
        string="Currency"
    )
    zip_code = fields.Char(
        string="Zip"
    )
    state_code = fields.Char(
        string="State"
    )
    country_code = fields.Char(
        string="Country"
    )
    wk_hash = fields.Char(
        string='Hash'
    )
    message = fields.Text(
        string='Message'
    )
    available = fields.Boolean()

    @staticmethod
    def generate_carrier_hash(values):
        """ Generate   Hash For Payment Validation."""
        _hash = ''
        for key in sorted(values):
            _hash += "&%s=%s" % ((key), (str(values[key])))
        _hash = _hash.strip('&')
        secure_hash = hmac.new(b'key', _hash.encode(), sha256).hexdigest()
        return secure_hash.upper()

    @classmethod
    def wk_generate_hash_domain(cls, carrier_id, order,  **kwargs):
        product_qty = order.order_line.filtered(
            lambda dol: not dol.is_delivery
        ).mapped(
            lambda ol: ('p%s_%s' % (ol.product_id.id, ol.product_qty))
        )
        wk_hash_vals = dict(
            product_qty='_'.join(product_qty),
            order_id=order.id,
            carrier_id='%s_%s' % (carrier_id.delivery_type, carrier_id.id),
        )
        wk_hash_vals.update(kwargs)
        wk_hash = cls.generate_carrier_hash(wk_hash_vals)
        return [
            ('wk_hash', '=', wk_hash),
        ]
