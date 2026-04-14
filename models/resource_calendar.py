from odoo import fields, models, api



class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    lateness_deducted_hourly_quarter = fields.Float(string='Hourly Lateness Deducted Quarter Day',default=1)
    lateness_deducted_hourly_half = fields.Float(string='Hourly Lateness Deducted Half Day',default=2)
    tolerance_deducted_minutes = fields.Integer(string='Tolerance Minutes for Lateness Deduction',default=15)
    tolerance_deducted_early_leave_minutes = fields.Integer(string='Tolerance Minutes for Early Leave Deduction',default=15)
    is_day_shift_intersected = fields.Boolean(string='Is Day Shift Intersected',default=False)

    # Days of week
    day_monday = fields.Boolean(string='Monday')
    day_tuesday = fields.Boolean(string='Tuesday')
    day_wednesday = fields.Boolean(string='Wednesday')
    day_thursday = fields.Boolean(string='Thursday')
    day_friday = fields.Boolean(string='Friday')
    day_saturday = fields.Boolean(string='Saturday')
    day_sunday = fields.Boolean(string='Sunday')

    @property
    def selected_days(self):
        day_map = {
            'day_monday': 0,
            'day_tuesday': 1,
            'day_wednesday': 2,
            'day_thursday': 3,
            'day_friday': 4,
            'day_saturday': 5,
            'day_sunday': 6,
        }
        return [num for field, num in day_map.items() if getattr(self, field)]

