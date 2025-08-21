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
    work_with_attendance = fields.Boolean(string="Work With Attendance",store=True)
    daily_rate = fields.Float(string="Daily Rate", compute='_compute_daily_rate', store=True)
    hourly_rate = fields.Float(string="Hourly Rate", compute='_compute_hourly_rate', store=True)
    bonus_public_holiday = fields.Float(string="Bonus Public Holiday",default=0)
    @api.depends("wage")
    def _compute_daily_rate(self):
        for r in self:
            r.daily_rate = round(r.wage / 30, 2)

    @api.depends("daily_rate")
    def _compute_hourly_rate(self):
        for r in self:
            r.hourly_rate = r.daily_rate / 8

