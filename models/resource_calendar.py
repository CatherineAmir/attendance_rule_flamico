from odoo import fields, models, api


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    lateness_deducted_hourly_quarter = fields.Float(string='Hourly Lateness Deducted Quarter Day',default=1)
    lateness_deducted_hourly_half = fields.Float(string='Hourly Lateness Deducted Half Day',default=2)
    is_day_shift_intersected = fields.Boolean(string='Is Day Shift Intersected',default=False)
