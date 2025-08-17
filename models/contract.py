from odoo import fields, models, api


class Contract(models.Model):
    _inherit = 'hr.contract'

    take_overtime = fields.Boolean(string="Take Overtime",default=False)
    apply_lateness=fields.Boolean(string="Apply Lateness",default=False)
    absence=fields.Selection([
        ("no","No Deduction"),
        ("day_day","Day by day"),
        ("day_by_day_half","Day by day and half"),
    ],default='day_by_day_half')

