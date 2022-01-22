# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields,models

class ShowMessage(models.TransientModel):
    _name = 'sh.popup.message'
    _description = 'Helps User to know action was failure or successfull'