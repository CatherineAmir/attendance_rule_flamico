from odoo import fields, models, api

from odoo.addons.resource.models.utils import Intervals
from collections import defaultdict
from datetime import datetime, time, timedelta
from odoo.osv import expression
import pytz
class HrPayslip(models.Model):
    _inherit = 'hr.payslip'


    attendance_ids = fields.One2many('hr.attendance', 'slip_id')
    deducted_lateness_days = fields.Float(string='Deducted Lateness Days',default=0,tracking=True)
    deducted_lateness_amount = fields.Float(string='Deducted Lateness Amount',default=0,tracking=True)
    actual_deducted_lateness_amount = fields.Float(string='Actual Deducted Lateness Amount',tracking=True)

    deducted_absence_days = fields.Float(string='Deducted Absence Days', default=0,tracking=True)
    deducted_absence_amount = fields.Float(string='Deducted Absence Amount', default=0,tracking=True)
    actual_deducted_absence_amount = fields.Float(string='Actual Deducted Absence Amount', tracking=True)

    number_of_public_holidays = fields.Float(string='Number of Public Holidays', default=0, tracking=True)
    total_bonus_public_holiday = fields.Float(string='Bonus Public Holiday', default=0, tracking=True)

    early_leave_hours = fields.Float(string='Early Leave Hours', default=0,tracking=True)
    early_leave_amount = fields.Float(string='Early Leave Amount', default=0,tracking=True)
    actual_early_leave_amount = fields.Float(string='Actual Early Leave Amount', default=0,tracking=True)

    overtime_hours = fields.Float(string='Overtime Hours', default=0,compute='_compute_overtime_hours',tracking=True)
    lateness_policy = fields.Selection(related='contract_id.lateness_policy', string='Lateness Policy', store=True)
    weekly_reward = fields.Float(string='Weekly Reward', compute='_compute_weekly_reward', store=True)




    def compute_sheet(self):
        self._compute_lateness_days()
        self._calculate_lateness_deducted_amount()
        self._compute_absence_days()
        self._calculate_absence_deducted_amount()
        self._compute_public_holidays()
        self._compute_overtime_hours()
        self._compute_early_leave_hours()
        self._compute_weekly_reward()
        # self.compute_attendance_time_off()
        # self._compute_absence_days()
        super(HrPayslip, self).compute_sheet()

        return True

    @api.depends('attendance_ids','contract_id.weekly_reward')
    def _compute_weekly_reward(self):
        for rec in self:
            if rec.attendance_ids:
                attendance_days = rec.attendance_ids.filtered(lambda r: r.first_attendance)
                if len(attendance_days) > 0:
                    week_reward_value = rec.contract_id.weekly_reward
                    number_of_worked_days = len(set(rec.contract_id.resource_calendar_id.attendance_ids.filtered(
                        lambda r: not r.work_entry_type_id.is_leave).mapped('dayofweek')))
                    daily_reward = week_reward_value / number_of_worked_days
                    total_reward = daily_reward * len(attendance_days)
                    rec.weekly_reward = total_reward
            else:
                rec.weekly_reward = 0


    @api.depends('attendance_ids')
    def _compute_early_leave_hours(self):
        for rec in self:
            if rec.attendance_ids and rec.contract_id.apply_early_leaving:
                user_tz = pytz.timezone(self.env.user.tz or 'UTC')
                # get attendance grouped by day with min check in and max check out
                days_attendance_grouped = self.env['hr.attendance'].read_group(
                    domain=[('id', 'in', rec.attendance_ids.ids), ('check_out', '!=', False),
                            ('in_mode', '!=', 'technical')],
                    fields=['check_in:min', 'check_out:max', 'worked_hours:sum'],
                    groupby=['check_in:day'],
                    orderby='check_in:day asc',
                    lazy=False)
                # print("days_attendance_grouped", days_attendance_grouped)
                early_leave_deducted = 0

                for g in days_attendance_grouped:
                    # print("worked_hours", g.get('worked_hours'))
                    check_in_local = g.get('check_in').replace(tzinfo=pytz.UTC).astimezone(user_tz) if g.get(
                        'check_in') else None
                    check_out_local = g.get('check_out').replace(tzinfo=pytz.UTC).astimezone(
                        user_tz) if g.get('check_out') else None
                    last_check_out_float = ((check_out_local.hour * 60) + check_out_local.minute) / 60

                    # Get the default hour_to from working schedule
                    if rec.contract_id.resource_calendar_id.is_day_shift_intersected:
                        hour_to = min(rec.contract_id.resource_calendar_id.attendance_ids.filtered(
                            lambda r: r.dayofweek == str(check_out_local.date().weekday())).mapped('hour_to') or [20])
                    else:
                        hour_to = max(rec.contract_id.resource_calendar_id.attendance_ids.filtered(
                            lambda r: r.dayofweek == str(check_in_local.date().weekday())).mapped('hour_to') or [20])
                    # print("hour_to (original)", hour_to)

                    # Check for custom hour time off on this date
                    # Adjust this query based on your time off model structure
                    # date_start = check_in_local.date()
                    # date_end = check_out_local.date()

                    # Find time offs for this specific date
                    time_offs = self.env['hr.leave'].search([
                        ('employee_id', '=', rec.employee_id.id),
                        ('state', '=', 'validate'),
                        ('request_unit_hours', '=', True),  # Custom hours time off
                        ('request_date_from', '=', check_in_local.date()),
                    ])

                    # Calculate total approved custom hours for this day
                    approved_early_leave_hours = 0
                    if time_offs:
                        for time_off in time_offs:
                            # Convert time off dates to local timezone
                            # time_off_start = pytz.UTC.localize(time_off.date_from).astimezone(user_tz)
                            # time_off_end = pytz.UTC.localize(time_off.date_to).astimezone(user_tz)

                            # Check if time off is on the same day
                            if time_off.request_unit_hours and time_off.request_date_from == check_in_local.date():
                                time_off_start_float = float(time_off.request_hour_from)
                                time_off_end_float = float(time_off.request_hour_to)
                                if time_off_start_float >= last_check_out_float and time_off_end_float <= hour_to:
                                    approved_early_leave_hours += (time_off_end_float - time_off_start_float)
                            elif time_off.request_unit_half and time_off.request_date_from == check_in_local.date():
                                date_from_tz = pytz.UTC.localize(time_off.date_from).astimezone(user_tz)
                                date_to_tz = pytz.UTC.localize(time_off.date_to).astimezone(user_tz)
                                time_off_start_float = ((date_from_tz.hour * 60) + date_from_tz.minute) / 60
                                time_off_end_float = ((date_to_tz.hour * 60) + date_to_tz.minute) / 60
                                if round(time_off_start_float, 1) >= round(last_check_out_float, 1) and round(
                                        last_check_out_float, 1) <= hour_to:
                                    approved_early_leave_hours += (time_off_end_float - time_off_start_float)
                    # Adjust hour_to based on approved custom hours
                    adjusted_hour_to = hour_to - approved_early_leave_hours
                    # print("approved_early_leave_hours", approved_early_leave_hours)
                    # print("adjusted_hour_to", adjusted_hour_to)
                    # print("")
                    # Calculate early leave with adjusted hour_to
                    if last_check_out_float < adjusted_hour_to:
                        print("adjusted_hour_to",adjusted_hour_to)
                        print("last_check_out_float", last_check_out_float)
                        number_of_hours_early_leave = (adjusted_hour_to - last_check_out_float)
                        early_leave_deducted += number_of_hours_early_leave
                        print("number_of_minutes_early", early_leave_deducted)
                rec.early_leave_hours = early_leave_deducted
                rec.early_leave_amount = rec.early_leave_hours * rec.contract_id.hourly_rate
                rec.actual_early_leave_amount = rec.early_leave_amount
            else:
                rec.early_leave_hours = 0
                rec.early_leave_amount = 0
                rec.actual_early_leave_amount = 0

    @api.depends('attendance_ids')
    def _compute_overtime_hours(self):
        for rec in self:
            if rec.attendance_ids:
                overtime_hours = sum(rec.attendance_ids.filtered(lambda o: o.overtime_hours>0).mapped('overtime_hours'))
                print("overtime_hours:", overtime_hours)
                rec.overtime_hours = overtime_hours
            else:
                rec.overtime_hours = 0



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

    @api.depends('attendance_ids','lateness_policy')
    def _compute_lateness_days(self):
        for rec in self:
            if rec.attendance_ids:
                if rec.lateness_policy == 'no':
                    rec.deducted_lateness_days = 0
                    continue
                if rec.lateness_policy == 'apply_lateness_rules':
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
                    # print("attendences_deducted_half_day",attendances_deducted_half_day)
                    # print("attendances_deducted_quarter_day",attendances_deducted_quarter_day)
                    amount_in_days = (attendances_deducted_half_day*0.5) + (attendances_deducted_quarter_day*0.25)
                    # print("amount_in_days",amount_in_days)
                    rec.deducted_lateness_days = amount_in_days
                elif rec.lateness_policy == 'apply_lateness_hourly_quarter':
                    total_lateness_hours = sum(rec.attendance_ids.filtered(lambda o: o.lateness_deducted_hours>0).mapped('lateness_deducted_hours'))
                    # print("total_lateness_hours:", total_lateness_hours)
                    hours_worked = rec.contract_id.resource_calendar_id.hours_per_day
                    print("hours_worked:", hours_worked)
                    lateness_days = total_lateness_hours / hours_worked
                    # Round to nearest quarter day
                    lateness_days_rounded = lateness_days
                    print("lateness_days_rounded:", lateness_days_rounded)
                    rec.deducted_lateness_days = lateness_days_rounded
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
