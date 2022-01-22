from operator import mod
from odoo import fields, models
from datetime import date,datetime

class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self,vals):
        for rec in self:
            if rec.picking_id and 'date' in vals:
                vals['date'] =  rec.picking_id.scheduled_date
            
            return super(StockMove,self).write(vals)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def write(self,vals):
        for rec in self:
            if rec.move_id and 'date' in vals:
                vals['date'] =  rec.move_id.date
            
            return super(StockMoveLine,self).write(vals)
    
