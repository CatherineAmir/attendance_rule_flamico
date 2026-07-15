from odoo import fields, models, api


class Contract(models.Model):
    _inherit = 'hr.contract'

    take_overtime = fields.Boolean(string="Take Overtime",default=False,store=True,tracking=True)
    # apply_lateness=fields.Boolean(string="Apply Lateness",default=False,store=True)
    lateness_policy = fields.Selection([
        ("no","No Lateness Deduction"),
        ("apply_lateness_rules","Apply Lateness Rules Deduction"),
        ('apply_lateness_hourly_quarter','Apply Lateness Hourly Deduction'),
    ],default='no',string='Lateness Deduction Policy',tracking=True)
    apply_early_leaving=fields.Boolean(string="Apply Early Leaving Deduction (Hourly)",default=False,store=True,tracking=True)
    absence=fields.Selection([
        ("no","No Deduction"),
        ("day_day","Day by day"),
        ("day_by_day_half","Day by day and half"),
    ],default='day_by_day_half',tracking=True)
    work_with_attendance = fields.Boolean(string="Work With Attendance",store=True,tracking=True)
    daily_rate = fields.Float(string="Daily Rate", compute='_compute_daily_rate', store=True,tracking=True)
    hourly_rate = fields.Float(string="Hourly Rate", compute='_compute_hourly_rate', store=True,tracking=True)
    bonus_public_holiday = fields.Float(string="Bonus Public Holiday",default=0,store=True,tracking=True)
    overtime_hourly_rate = fields.Float(string="Overtime Hourly Rate",tracking=True)
    @api.depends("wage")
    def _compute_daily_rate(self):
        for r in self:
            r.daily_rate = round(r.wage / 30, 2)

    @api.depends("daily_rate","resource_calendar_id")
    def _compute_hourly_rate(self):
        for r in self:
            if r.resource_calendar_id:
                r.hourly_rate = r.daily_rate / (r.resource_calendar_id.hours_per_day or 8)

