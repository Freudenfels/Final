from odoo import fields, models, api, _


class ResCompanyEpt(models.Model):
    _inherit = 'res.company'
    street_no = fields.Char('Street No.')

    use_dhl_paket_shipping_provider = fields.Boolean(copy=False, string="Are You Using DHL Packet?",
                                               help="If you use DHL Packet integration then set value to TRUE.",
                                               default=False)
    userid = fields.Char("DHL UserId", copy=False,
                         help="When use the sandbox account developer id use as the userId.When use the live account application id use as the userId.")
    password = fields.Char("DHL Password", copy=False,
                           help="When use the sandbox account developer portal password use to as the password.When use the live account application token use to as the password.")

    http_userid = fields.Char("HTTP UserId", copy=False, help="HTTP Basic Authentication.")
    http_password = fields.Char("HTTP Password", copy=False, help="HTTP Basic Authentication.")
    dhl_ekp_no = fields.Char("EKP Number", copy=False,
                             help="The EKP number sent to you by DHL and it must be maximum 10 digit allow.")
    tracking_link = fields.Char(string="DHL Packet Tracking URL")

    dhl_street_no = fields.Many2one('ir.model.fields', string='Street No.',
                                    domain="[('model','=','res.partner'),('ttype','=','char')]",
                                    help="Street number is require when use defualt address.")
    dhl_packstation_postnumber = fields.Many2one('ir.model.fields', string='Post Number',
                                                 domain="[('model','=','res.partner'),('ttype','=','char')]",
                                                 help="Post Number of the receiver, if not set receiver e-mail and/or mobilephone number needs to be set.")
    dhl_packstation_prefix = fields.Char("Prefix", help="Packstation Prefix.")
    dhl_packstation_no = fields.Many2one('ir.model.fields', string='No.',
                                         domain="[('model','=','res.partner'),('ttype','=','char')]")
    dhl_filiale_postnumber = fields.Many2one('ir.model.fields', string='Post Number',
                                             domain="[('model','=','res.partner'),('ttype','=','char')]",
                                             help="Post Number of the receiver, if not set receiver e-mail and/or mobilephone number needs to be set.")
    dhl_filiale_prefix = fields.Char("Prefix", help="Postfiliale Prefix")
    dhl_filiale_no = fields.Many2one('ir.model.fields', string='No.',
                                     domain="[('model','=','res.partner'),('ttype','=','char')]",
                                     help="Postfiliale number,max length is 3.")
    dhl_parcelshop_prefix = fields.Char("Prefix", help="ParcelShop Prefix")
    dhl_parcelshop_no = fields.Many2one('ir.model.fields', string='No.',
                                        domain="[('model','=','res.partner'),('ttype','=','char')]",
                                        help="ParcelShop number,max length is 3.")