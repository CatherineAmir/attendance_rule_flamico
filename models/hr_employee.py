from odoo import fields, models, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'


    parent_department_id = fields.Many2one(related='department_id.parent_id',string='Parent Department',store=True)
