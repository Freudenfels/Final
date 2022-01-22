# -*- coding: utf-8 -*-
#################################################################################
##    Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
from odoo import fields ,models
ComputeWeight = [
    ('volume','Using Volumetric Weight'),
    ('weight','Using Weight')
]
class res_config_settings(models.TransientModel):
	_inherit='res.config.settings'

	module_hermes_delivery_carrier=fields.Boolean(
		string= "Hermes Shipping Service"
	)
	module_acs_shipping_integration=fields.Boolean(
		string = "ACS Courier Settings"
	)
	module_apc_shipping_integration=fields.Boolean(
		string = "APC Overnight Settings"
	)
	module_fedex_delivery_carrier=fields.Boolean(
		string = "FedEx Shipping Service"
	)
	module_usps_delivery_carrier=fields.Boolean(
		string = "USPS Shipping Service"
	)
	module_ups_delivery_carrier=fields.Boolean(
		string = "UPS Shipping Service"
	)
	module_dhl_delivery_carrier=fields.Boolean(
		string = "DHL Shipping Service"
	)
	module_auspost_delivery_carrier = fields.Boolean(
		string = "Australia Post Shipping Service"
	)
	module_dhl_intraship_delivery_carrier=fields.Boolean(
		string = "DHL Intraship Shipping Service"
	)
	module_aramex_delivery_carrier = fields.Boolean(
		string = "Aramex Shipping Service"
	)
	module_canada_post_shipping_integration = fields.Boolean(
		string = "Canada Post Shipping Integration"
	)
	
	compute_weight = fields.Selection(
		selection = ComputeWeight,
		default='weight',
		string= 'Compute Weight'
	)