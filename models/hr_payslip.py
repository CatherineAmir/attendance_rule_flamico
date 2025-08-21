from odoo import fields, models, api

from odoo.addons.resource.models.utils import Intervals
from collections import defaultdict
from datetime import datetime, time, timedelta
from odoo.osv import expression
class HrPayslip(models.Model):
    _inherit = 'hr.payslip'


    attendance_ids = fields.One2many('hr.attendance', 'slip_id')
    deducted_lateness_days = fields.Float(string='Deducted Lateness Days',default=0)
    deducted_lateness_amount = fields.Float(string='Deducted Lateness Amount',default=0)
    actual_deducted_lateness_amount = fields.Float(string='Actual Deducted Lateness Amount')

    deducted_absence_days = fields.Float(string='Deducted Absence Days', default=0)
    deducted_absence_amount = fields.Float(string='Deducted Absence Amount', default=0)
    actual_deducted_absence_amount = fields.Float(string='Actual Deducted Absence Amount')

    number_of_public_holidays = fields.Float(string='Number of Public Holidays', default=0)
    total_bonus_public_holiday = fields.Float(string='Bonus Public Holiday', default=0)





    def compute_sheet(self):
        self._compute_lateness_days()
        self._calculate_lateness_deducted_amount()
        self._compute_absence_days()
        self._calculate_absence_deducted_amount()
        self._compute_public_holidays()
        # self.compute_attendance_time_off()
        # self._compute_absence_days()
        super(HrPayslip, self).compute_sheet()

        return True

    @api.depends('attendance_ids')
    def _compute_public_holidays(self):
        for rec in self:
            number_of_public_holidays = rec.attendance_ids.filtered(lambda r: r.is_public_holiday)
            print("Number of Public Holidays:", len(number_of_public_holidays))
            if len(number_of_public_holidays) > 0:
                rec.number_of_public_holidays = len(number_of_public_holidays)
                rec.total_bonus_public_holiday = rec.number_of_public_holidays * rec.employee_id.contract_id.bonus_public_holiday
            else:
                rec.number_of_public_holidays = 0
                rec.total_bonus_public_holiday = 0


    # @api.depends('attendance_ids')
    # def _compute_absence_days(self):
    #     for rec in self:
    #         attendance_absence_ids = rec.attendance_ids.filtered(lambda r: r.in_mode == 'technical')
    #         print("attendance_absence_ids", len(attendance_absence_ids))
    #         if rec.contract_id.absence == 'no':
    #             rec.deducted_absence_days = 0
    #         elif rec.contract_id.absence == 'day_day':
    #             days_count = 0
    #             for attendance_absence in attendance_absence_ids:
    #                 if attendance_absence.is_leave:
    #                     print("attendance_absence", attendance_absence.check_in)
    #                     base_day = attendance_absence.check_in.date()
    #                     prev_day = base_day - timedelta(days=1)
    #                     next_day = base_day + timedelta(days=1)
    #                     print("prev_day", prev_day)
    #                     print("next_day", next_day)
    #                     absence_day_before = rec.attendance_ids.filtered(lambda r: r.check_in.date() == prev_day and r.)

    # def compute_attendance_time_off(self):
    #     for r in self:
    #         date_from = r.date_from
    #         date_to = r.date_to
    #
    #         work_enteries = self.env['hr.work.entry'].search([("employee_id", "=", r.employee_id.id),
    #                                                           ("date_start", '>=', fields.datetime.combine(date_from,
    #                                                                                                        fields.datetime.min.time())),
    #                                                           ("date_start", '<=', fields.datetime.combine(date_to,
    #                                                                                                        fields.datetime.max.time()))])
    #         print("work_enteries", work_enteries)
    #         print("len(work_enteries)", len(work_enteries))
    #         for attendance in r.attendance_ids:
    #             check_in_date = attendance.check_in.date()
    #             min_check_in_date = fields.datetime.combine(check_in_date, fields.datetime.min.time())
    #             max_check_in_date = fields.datetime.combine(check_in_date, fields.datetime.max.time())
    #             print("min_check_in_date", min_check_in_date)
    #             print("max_check_in_date", min_check_in_date)
    #             work_entry = work_enteries.filtered(
    #                 lambda
    #                     w: w.date_start >= min_check_in_date and w.date_start <= max_check_in_date and w.state not in [
    #                     'cancelled', 'conflict']),
    #             print("work_entry", work_entry)
    #             if len(work_entry) == 1:
    #                 print("if work_entry[0].work_entry_type_id", work_entry[0].work_entry_type_id)
    #                 print("work_entry[0].work_entry_type_id", work_entry[0].work_entry_type_id.mapped("name"))
    #                 print("work_entry[0].work_entry_type_id", work_entry[0].read())
    #                 leaves = work_entry[0].work_entry_type_id.mapped("is_leave")
    #                 print("leaves", leaves)
    #                 # leaves_compensation = work_entry[0].work_entry_type_id.mapped("compensation")
    #                 # print("leaves_compensation", leaves_compensation)
    #                 # print("all(leaves_compensation)", all(leaves_compensation))
    #                 # if all(leaves_compensation):
    #                 #     attendance.is_compensation = True
    #                 # else:
    #                 #     attendance.is_compensation = False
    #                 if all(leaves):
    #
    #                     attendance.is_leave = True
    #                 else:
    #                     attendance.is_leave = False

    @api.depends('attendance_ids')
    def _compute_absence_days(self):
        for rec in self:
            if rec.attendance_ids:
                attendance_absence_deducted_day_by_day = self.env['hr.attendance'].search_count(
                    domain=[
                        ('id','in',rec.attendance_ids.ids),
                        ('in_mode','=','technical'),
                        ('absence','=','day_day')
                    ]
                )
                attendance_absence_deducted_day_by_day_half = self.env['hr.attendance'].search_count(
                    domain=[
                        ('id', 'in', rec.attendance_ids.ids),
                        ('in_mode', '=', 'technical'),
                        ('absence', '=', 'day_by_day_half')
                    ]
                )
                total_deducted_days = attendance_absence_deducted_day_by_day + (attendance_absence_deducted_day_by_day_half * 1.5)
                print("total_deducted_days:", total_deducted_days)
                rec.deducted_absence_days = total_deducted_days
                print("deducted_absence_days:", rec.deducted_absence_days)
            else:
                rec.deducted_absence_days = 0

    @api.depends('deducted_lateness_days')
    def _calculate_absence_deducted_amount(self):
        for rec in self:
            if rec.deducted_absence_days != 0:
                rec.deducted_absence_amount = rec.deducted_absence_days * rec.contract_id.daily_rate
                rec.actual_deducted_absence_amount = rec.deducted_absence_amount
            else:
                rec.deducted_absence_amount = 0
                rec.actual_deducted_absence_amount = 0

    @api.depends('attendance_ids')
    def _compute_lateness_days(self):
        for rec in self:
            if rec.attendance_ids:
                attendances_deducted_half_day = self.env['hr.attendance'].search_count(domain=[
                    ('id','in',rec.attendance_ids.ids),
                    ('in_mode','=','manual'),
                    ('first_attendance','=',True),
                    ('lateness_deducted','=','half_day'),

                ])
                attendances_deducted_quarter_day = self.env['hr.attendance'].search_count(domain=[
                    ('id', 'in', rec.attendance_ids.ids),
                    ('in_mode', '=', 'manual'),
                    ('first_attendance', '=', True),
                    ('lateness_deducted', '=', 'quarter_day'),
                ])
                print("attendences_deducted_half_day",attendances_deducted_half_day)
                print("attendances_deducted_quarter_day",attendances_deducted_quarter_day)
                amount_in_days = (attendances_deducted_half_day*0.5) + (attendances_deducted_quarter_day*0.25)
                print("amount_in_days",amount_in_days)
                rec.deducted_lateness_days = amount_in_days
            else:
                rec.deducted_lateness_days = 0


    @api.depends('deducted_lateness_days')
    def _calculate_lateness_deducted_amount(self):
        for rec in self:
            if rec.deducted_lateness_days != 0:
                rec.deducted_lateness_amount = rec.deducted_lateness_days * rec.contract_id.daily_rate
                rec.actual_deducted_lateness_amount = rec.deducted_lateness_amount
            else:
                rec.deducted_lateness_amount = 0
                rec.actual_deducted_lateness_amount = 0





    def _get_attendance_by_payslip(self):
        """
            Find all attendances linked to payslips.

            Note: An attendance is linked to a payslip if it has
            the same employee and the time periods correspond.

            :return: dict with:
                        - key = payslip record
                        - value = attendances recordset linked to payslip
        """
        attendance_by_payslip = defaultdict(lambda: self.env['hr.attendance'])
        slip_by_employee = defaultdict(lambda: self.env['hr.payslip'])
        attendance_domains = []
        for slip in self:
            if slip.contract_id.work_entry_source != 'attendance' and not slip.contract_id.work_with_attendance:
                continue
            slip_by_employee[slip.employee_id.id] |= slip
            attendance_domains.append([
                ('employee_id', '=', slip.employee_id.id),
                ('check_in', '<=', slip.date_to),
                ('check_out', '>=', slip.date_from),
            ])
        attendance_group = self.env['hr.attendance']._read_group(
            expression.OR(attendance_domains),
            groupby=['employee_id', 'check_in:day'],
            aggregates=['id:recordset'],
        )
        for employee, check_in, attendance in attendance_group:
            for slip in slip_by_employee[employee.id]:
                if slip.date_from <= check_in.date() <= slip.date_to:
                    attendance_by_payslip[slip] |= attendance

                    attendance.slip_id = slip.id
        return attendance_by_payslip
