from odoo import models, fields, api, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    recipient_addess_type = fields.Selection(
            [('dhl_street', ' Street'), ('dhl_packstation', ' Packstation'),
             ('dhl_filiale', ' Filiale'), ('dhl_parcelshop', ' Parcelshop')],
            'Recipient Address Type', required=True,help="Select the Recipient address type and set method.", default="dhl_street")
