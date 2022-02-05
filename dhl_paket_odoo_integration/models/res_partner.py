
from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'
    street_no = fields.Char('Street No.')
