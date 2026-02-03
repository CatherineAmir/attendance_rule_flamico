from odoo import fields, models, api


class AbsenseDeduction(models.TransientModel):
    _name = 'absence.deduction'
    _description = 'Absence Deduction'

    date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    number_of_days = fields.Integer(string="Number of Days",
                                    help="Number of days to to detect absence from this machine.",
                                    compute="_compute_number_of_days")

    @api.depends('date', 'end_date')
    def _compute_number_of_days(self):
        for rec in self:
            if rec.date and rec.end_date:
                delta = rec.end_date - rec.date
                rec.number_of_days = delta.days + 1
            else:
                rec.number_of_days = 0


    def action_absence_deduction(self):
        """Detect absences and apply deductions based on the specified date range and number of days.
        """
        self.ensure_one()
        attendance_obj = self.env['hr.attendance']
        attendance_obj.cron_absence_detection(self.number_of_days - 1, self.end_date)