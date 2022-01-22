from operator import mod
from odoo import fields, models
from datetime import date,datetime

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def write(self,vals):
        for rec in self:
            if rec.sale_id and 'date_done' in vals:
                vals['date_done'] =  rec.sale_id.date_order
            
            return super(StockPicking,self).write(vals)