from odoo import fields, models, api


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    lateness_deducted_hourly_quarter = fields.Float(string='Hourly Lateness Deducted Quarter Day',default=1)
    lateness_deducted_hourly_half = fields.Float(string='Hourly Lateness Deducted Half Day',default=2)
    tolerance_deducted_minutes = fields.Integer(string='Tolerance Minutes for Lateness Deduction',default=15)
    tolerance_deducted_early_leave_minutes = fields.Integer(string='Tolerance Minutes for Early Leave Deduction',default=15)
    is_day_shift_intersected = fields.Boolean(string='Is Day Shift Intersected',default=False)
