from odoo import fields, models, api, _

from datetime import datetime, time, date
from dateutil.relativedelta import relativedelta
import pytz
from pytz import timezone, utc
from odoo.addons.resource.models.utils import Intervals
from datetime import timedelta
from collections import defaultdict
local_tz = timezone('Africa/Cairo')


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    first_attendance = fields.Boolean(string='is First Attendance', default=False,
                                      compute='_calculate_first_attendance', store=True)
    lateness_deducted = fields.Selection([('none', 'None'), ('quarter_day', 'Quarter Day'), ('half_day', 'Half Day')],
                                         default='none', string='Lateness Deduction',
                                         compute='_calculate_lateness_deducted', store=True)
    lateness_deducted_hours = fields.Float(string='Lateness Deducted Hours', compute='_compute_lateness_deducted_hours',
                                           store=True,help="Total number of hours to be deducted due to lateness based on hourly quarter policy.")
    slip_id = fields.Many2one('hr.payslip', string='Slip')
    is_leave = fields.Boolean(default=False, store=True)
    absence = fields.Selection([
        ("no", "No Deduction"),
        ("day_day", "Day by day"),
        ("day_by_day_half", "Day by day and half"),
    ], default='no', string='Absence Deduction')
    is_public_holiday = fields.Boolean(default=False, string='Is Public Holiday', store=True,
                                       compute='_is_public_holiday')
    lateness_policy = fields.Selection(related='employee_id.contract_id.lateness_policy', string='Lateness Policy',
                                       store=True)

    @api.depends('check_in', 'first_attendance', 'employee_id')
    def _compute_lateness_deducted_hours(self):
        for rec in self:
            if rec.first_attendance and rec.employee_id and rec.employee_id.contract_id.work_with_attendance and rec.employee_id.contract_id.lateness_policy == 'apply_lateness_hourly_quarter':
                schedule_id = rec.employee_id.resource_calendar_id
                if schedule_id.is_day_shift_intersected:
                    work_from = max(list(sorted(set(schedule_id.attendance_ids.mapped('hour_from')))))
                else:
                    work_from = min(list(sorted(set(schedule_id.attendance_ids.mapped('hour_from')))))
                calendar = rec._get_employee_calendar()
                resource = rec.employee_id.resource_id
                tz = timezone(resource.tz) if not calendar else timezone(calendar.tz)
                """
                check approve lateness timeOff Custom hours 
                """
                check_in_local = rec.check_in.astimezone(tz)
                approved_late_arrival_hours = 0
                time_offs = self.env['hr.leave'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('state', '=', 'validate'),
                    '|',
                    ('request_unit_hours', '=', True),  # Custom hours time off
                    ('request_unit_half', '=', True),  # half day time off
                    ('request_date_from', '=', check_in_local.date()),
                ])
                for time_off in time_offs:
                    # Check if time off is on the same day and covers beginning of day
                    if time_off.request_unit_hours:
                        if time_off.request_date_from == check_in_local.date():
                            time_off_start_float = float(time_off.request_hour_from)
                            time_off_end_float = float(time_off.request_hour_to)
                            # If time off starts at or before working hours
                            if time_off_start_float <= work_from:
                                approved_late_arrival_hours += (time_off_end_float - work_from)
                    elif time_off.request_unit_half:
                        if time_off.request_date_from == check_in_local.date():
                            date_from_tz = time_off.date_from.astimezone(tz)
                            date_to_tz = time_off.date_to.astimezone(tz)

                            time_off_start_float = ((date_from_tz.hour * 60) + date_from_tz.minute) / 60
                            time_off_end_float = ((date_to_tz.hour * 60) + date_to_tz.minute) / 60
                            if round(time_off_start_float, 1) <= work_from:
                                # Calculate approved late arrival hours
                                approved_late_arrival_hours += (round(time_off_end_float, 1) - work_from)

                working_hour_from = work_from + approved_late_arrival_hours

                check_in_float = check_in_local.hour + (check_in_local.minute / 60)
                lateness_hours = check_in_float - working_hour_from
                print("lateness_hours", lateness_hours)
                print("check_in_float",check_in_float)
                print("working_hour_from",working_hour_from)
                tolerance_deducted_hours = schedule_id.tolerance_deducted_minutes / 60
                if lateness_hours >= tolerance_deducted_hours:
                    rec.lateness_deducted_hours = lateness_hours
                else:
                    rec.lateness_deducted_hours = 0.0
            else:
                rec.lateness_deducted_hours = 0.0

    # is_time_off = fields.Boolean(default=False, string='Is Time Off (Approved)',store=True)

    # def _is_time_off_approved(self,technical_attendances):
    #     for rec in technical_attendances:
    #         time_offs = self.env['hr.leave'].search([('employee_id', '=', rec.employee_id.id),('state','=','validate')])
    #         print("time_off", time_offs)
    #         if len(time_offs) > 0:
    #             for time_off in time_offs:
    #                 start_date = time_off.request_date_from
    #                 end_date = time_off.request_date_to
    #                 all_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    #                 print("all_dates:", all_dates)
    #                 if rec.check_in.date() in all_dates and rec.in_mode == 'technical':
    #                     rec.is_time_off = True
    #         else:
    #             rec.is_time_off = False
    @api.depends('worked_hours', 'is_public_holiday')
    def _compute_overtime_hours(self):
        super()._compute_overtime_hours()

        for attendance in self:
            if attendance.is_public_holiday:
                weekday_attendances = attendance.employee_id.resource_calendar_id.attendance_ids.filtered(
                    lambda r: r.dayofweek == str(attendance.check_in.weekday())
                )

                if weekday_attendances:
                    if attendance.employee_id.contract_id.resource_calendar_id.is_day_shift_intersected:
                        work_from = max(weekday_attendances.mapped('hour_from'))
                        work_to = min(weekday_attendances.mapped('hour_to'))
                        hours_worked = (24 - work_from) + work_to
                    else:
                        work_from = min(weekday_attendances.mapped('hour_from'))
                        work_to = max(weekday_attendances.mapped('hour_to'))
                        hours_worked = work_to - work_from

                    attendance.overtime_hours = attendance.worked_hours - hours_worked
                else:
                    attendance.overtime_hours = 0

    @api.depends('first_attendance', 'check_in')
    def _is_public_holiday(self):
        for rec in self:
            if rec.check_in and rec.first_attendance:
                check_in_date = rec.check_in.date()
                start = datetime.combine(check_in_date, time.min)
                # print("start date:", start <= datetime(2026, 1, 29, 0, 0))
                end = start + relativedelta(days=1)
                # print("end date:", end > datetime(2026, 1, 29, 23, 59))
                prev_day_attendance = self.env['resource.calendar.leaves'].search(
                    [('date_from', '<=', end),
                     ('date_to', '>=', start),
                     ('resource_id', '=', False),
                     ])
                print("prev_day_attendance", prev_day_attendance.read(['name', 'date_from', 'date_to']))
                if len(prev_day_attendance) > 0:
                    rec.is_public_holiday = True
                else:
                    rec.is_public_holiday = False

    def detect_absence_state(self, technical_attendances):
        for rec in technical_attendances:
            if rec.in_mode == 'technical':
                if rec.employee_id.contract_id.absence == 'no':
                    rec.absence = 'no'
                elif rec.employee_id.contract_id.absence == 'day_day':
                    # check if the previous day of holiday is absence
                    if rec.is_leave:
                        base_day = rec.check_in.date()
                        prev_day = base_day - relativedelta(days=1)
                        start = datetime.combine(prev_day, time.min)
                        end = start + relativedelta(days=1)
                        prev_day_attendance = self.env['hr.attendance'].search(
                            [('employee_id', '=', rec.employee_id.id), ('id', '!=', rec.id), ('check_in', '>=', start),
                             ('check_in', '<', end)], order='check_in asc')
                        if len(prev_day_attendance) > 0:
                            if prev_day_attendance[0].in_mode == 'technical' and not prev_day_attendance[0].is_leave:
                                rec.absence = 'day_day'
                            else:
                                rec.absence = 'no'
                        else:
                            ######################### might the previous day is public holiday #####################
                            rec.absence = 'no'
                    else:
                        rec.absence = 'day_day'
                elif rec.employee_id.contract_id.absence == 'day_by_day_half':
                    base_day = rec.check_in.date()
                    # print("check_in:", base_day)
                    prev_day = base_day - relativedelta(days=1)
                    start = datetime.combine(prev_day, time.min)
                    end = start + relativedelta(days=1)
                    prev_day_attendance = self.env['hr.attendance'].search(
                        [('employee_id', '=', rec.employee_id.id), ('id', '!=', rec.id), ('check_in', '>=', start),
                         ('check_in', '<', end)], order='check_in asc')
                    # print("prev_day_attendance",prev_day_attendance.check_in)
                    if len(prev_day_attendance) > 0:
                        if rec.is_leave:
                            if prev_day_attendance[0].in_mode == 'technical' and not prev_day_attendance[0].is_leave:
                                rec.absence = 'day_day'
                            else:
                                rec.absence = 'no'
                        # elif rec.is_time_off:
                        #     rec.absence = 'no'
                        else:
                            if prev_day_attendance[0].absence == 'day_day':
                                rec.absence = 'day_by_day_half'
                            elif prev_day_attendance[0].absence == 'day_by_day_half':
                                rec.absence = 'day_by_day_half'
                            elif prev_day_attendance[0].absence == 'no':
                                rec.absence = 'day_day'
                    else:
                        rec.absence = 'day_day'
                else:
                    rec.absence = 'no'

    def detect_is_timeoff(self, technical_attendances):
        for rec in technical_attendances:
            if rec.in_mode == 'technical':
                check_in_date = rec.check_in.date().weekday()
                # check if the day is paid time off from working scheduale
                day_off = rec.employee_id.contract_id.resource_calendar_id.attendance_ids.filtered(
                    lambda d: d.dayofweek == str(check_in_date) and d.work_entry_type_id.is_leave)
                ################### time off criteria ######################
                ###########################################################
                if len(day_off):
                    rec.is_leave = True

    def calculate_test_button(self):
        self._calculate_lateness_deducted()
        # self._is_time_off_approved()
        # self.detect_is_timeoff()
        # self.detect_absence_state()

    def add_float_hours_to_time(self, base_hours, float_hours):
        total_float_hours = base_hours + float_hours
        hours = int(total_float_hours)
        minutes = int((total_float_hours - hours) * 60)
        if minutes >= 60:
            hours += minutes // 60
            minutes = minutes % 60

        hours = hours % 24

        return time(hours, minutes, 0)

    @api.depends('check_in', 'first_attendance')
    def _calculate_lateness_deducted(self):
        for rec in self:
            schedule_id = rec.employee_id.resource_calendar_id
            if schedule_id.is_day_shift_intersected:
                work_from = max(list(sorted(set(schedule_id.attendance_ids.mapped('hour_from') if schedule_id.attendance_ids else [8]))))
            else:
                work_from = min(list(sorted(set(schedule_id.attendance_ids.mapped('hour_from') if schedule_id.attendance_ids else [8]))))
            # work_from = list(sorted(set(schedule_id.attendance_ids.mapped('hour_from'))))
            print("work_from", work_from)
            calendar = rec._get_employee_calendar()
            resource = rec.employee_id.resource_id
            tz = timezone(resource.tz) if not calendar else timezone(calendar.tz)
            working_hours = work_from
            print("working_hours", working_hours)
            if rec.first_attendance:
                if rec.employee_id.contract_id.work_with_attendance and rec.employee_id.contract_id.lateness_policy == 'apply_lateness_rules':
                    """
                                    check approve lateness timeOff Custom hours 
                                    """
                    check_in_local = rec.check_in.astimezone(tz)
                    approved_late_arrival_hours = 0
                    time_offs = self.env['hr.leave'].search([
                        ('employee_id', '=', rec.employee_id.id),
                        ('state', '=', 'validate'),
                        '|',
                        ('request_unit_hours', '=', True),  # Custom hours time off
                        ('request_unit_half', '=', True),  # half day time off
                        ('request_date_from', '=', check_in_local.date()),
                    ])
                    for time_off in time_offs:
                        # Check if time off is on the same day and covers beginning of day
                        if time_off.request_unit_hours:
                            if time_off.request_date_from == check_in_local.date():
                                time_off_start_float = float(time_off.request_hour_from)
                                time_off_end_float = float(time_off.request_hour_to)
                                # If time off starts at or before working hours
                                if time_off_start_float <= work_from:
                                    approved_late_arrival_hours += (time_off_end_float - work_from)
                        elif time_off.request_unit_half:
                            if time_off.request_date_from == check_in_local.date():
                                date_from_tz = time_off.date_from.astimezone(tz)
                                date_to_tz = time_off.date_to.astimezone(tz)

                                time_off_start_float = ((date_from_tz.hour * 60) + date_from_tz.minute) / 60
                                time_off_end_float = ((date_to_tz.hour * 60) + date_to_tz.minute) / 60
                                if round(time_off_start_float, 1) <= work_from:
                                    # Calculate approved late arrival hours
                                    approved_late_arrival_hours += (round(time_off_end_float, 1) - work_from)

                    working_hours = work_from + approved_late_arrival_hours

                    tolerance_quarter_hourly_lateness = schedule_id.lateness_deducted_hourly_quarter
                    tolerance_half_hourly_lateness = schedule_id.lateness_deducted_hourly_half
                    check_in_date = rec.check_in.date()
                    custom_time_quarter_day = rec.add_float_hours_to_time(working_hours,
                                                                          tolerance_quarter_hourly_lateness)
                    custom_time_half_day = rec.add_float_hours_to_time(working_hours, tolerance_half_hourly_lateness)
                    max_check_in_quarter = datetime.combine(check_in_date, custom_time_quarter_day)
                    max_check_in_tz_quarter = tz.localize(max_check_in_quarter)
                    max_check_in_half = datetime.combine(check_in_date, custom_time_half_day)
                    max_check_in_tz_half = tz.localize(max_check_in_half)
                    check_in_tz = rec.check_in.astimezone(tz)
                    if check_in_tz > max_check_in_tz_half:
                        rec.lateness_deducted = 'half_day'
                        continue
                    elif check_in_tz > max_check_in_tz_quarter:
                        rec.lateness_deducted = 'quarter_day'
                        continue
                    else:
                        rec.lateness_deducted = 'none'
                else:
                    rec.lateness_deducted = 'none'
            else:
                rec.lateness_deducted = 'none'

    # def _cron_absence_detection(self):
    #     """
    #     Objective is to create technical attendances on absence days to have negative overtime created for that day
    #     """
    #     number_of_days = 40
    #     # yesterday = datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=1)
    #
    #     companies = self.env['res.company'].search([('absence_management', '=', True)])
    #     if not companies:
    #         return
    #
    #     for d in range(1, number_of_days + 1):
    #         technical_attendances_vals = []
    #         day = datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=number_of_days - d)
    #         print("day", day)
    #         today = datetime.today()
    #         if today == day:
    #             break
    #
    #         checked_in_employees = self.env['hr.attendance.overtime'].search([('date', '=', day),
    #                                                                           ('adjustment', '=', False)]).employee_id
    #
    #         # print("checked_in_employees", checked_in_employees.mapped("name"))
    #         absent_employees = self.env['hr.employee'].search([('id', 'not in', checked_in_employees.ids),
    #                                                            ('company_id', 'in', companies.ids)])
    #         # print("absent_employees", absent_employees.mapped("name"))
    #
    #         for emp in absent_employees:
    #             schedule_id = emp.contract_id.resource_calendar_id
    #             # print("schedule_id", schedule_id)
    #
    #             work_from = list(sorted(set(schedule_id.attendance_ids.mapped('hour_from'))))
    #             if len(work_from):
    #                 # print("work_from", work_from)
    #                 start_hour = int(work_from[0])
    #             else:
    #                 start_hour = 9
    #
    #             # print("start_hour", start_hour)
    #             local_day_start = pytz.utc.localize(day).astimezone(pytz.timezone(emp._get_tz())) + relativedelta(
    #                 hours=start_hour)
    #
    #             # print("local_day_start", local_day_start)
    #             technical_attendances_vals.append({
    #                 'check_in': local_day_start.strftime('%Y-%m-%d %H:%M:%S'),
    #                 'check_out': (local_day_start + relativedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S'),
    #                 'in_mode': 'technical',
    #                 'out_mode': 'technical',
    #                 'employee_id': emp.id
    #             })
    #
    #         # print("technical_attendances_vals", technical_attendances_vals)
    #         technical_attendances = self.env['hr.attendance'].create(technical_attendances_vals)
    #
    #         to_unlink = technical_attendances.filtered(lambda a: a.overtime_hours == 0)
    #
    #         body = _('This attendance was automatically created to cover an unjustified absence on that day.')
    #         for technical_attendance in technical_attendances - to_unlink:
    #             technical_attendance.message_post(body=body)
    #
    #         to_unlink.unlink()
    #
    #         self.env.cr.commit()
    #         self.env.cr.savepoint()
    #         self.env.flush_all()

    def cron_absence_detection(self,number_of_days=30,end_date=None):
        """
        Objective is to create technical attendances on absence days to have negative overtime created for that day
        """
        # number_of_days = 20
        # yesterday = datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=1)

        companies = self.env['res.company'].search([('absence_management', '=', True)])
        if not companies:
            return

        TARGET_EMP_ID = 10570  # NEW: limit cron to this employee only
        if end_date is None:
            end_date = datetime.today()
        elif isinstance(end_date, date) and not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.min.time())
        for d in range(0, number_of_days + 1):
            technical_attendances_vals = []
            day = end_date.replace(hour=0, minute=0, second=0) - relativedelta(days=number_of_days - d)
            print("day", day)
            today = datetime.today()
            # print("today", today)
            if today.date() == day.date():
                print("im breaking")
                break

            # CHANGED: only check overtime for the target employee
            # checked_in_employees = self.env['hr.attendance.overtime'].search([
            #     ('date', '=', day),
            #     ('adjustment', '=', False),
            #     ('employee_id', '=', TARGET_EMP_ID),  # NEW
            # ]).employee_id
            checked_in_employees = self.env['hr.attendance'].search([

                ('check_in', '>=', fields.datetime.combine(day.date(), fields.datetime.min.time())),
                ('check_in', '<=', fields.datetime.combine(day.date(), fields.datetime.max.time())),
                ('employee_id', '=', TARGET_EMP_ID),
            ]
            ).employee_id
            # CHANGED: only consider the target employee, and only if absent
            absent_employees = self.env['hr.employee'].search([
                ('id', '=', TARGET_EMP_ID),  # NEW
                ('id', 'not in', checked_in_employees.ids),
                ('company_id', 'in', companies.ids),
            ])

            for emp in absent_employees:
                schedule_id = emp.contract_id.resource_calendar_id
                work_from = list(sorted(set(schedule_id.attendance_ids.mapped('hour_from'))))
                if len(work_from):
                    # print("work_from", work_from)
                    start_hour = int(
                        max(work_from) if emp.contract_id.resource_calendar_id.is_day_shift_intersected else work_from[
                            0])
                    print("start_hour", start_hour)
                else:
                    start_hour = 9

                local_day_start = local_tz.localize(day) + relativedelta(
                    hours=start_hour)
                # print("local_day_start", local_day_start)
                # naive_dt = datetime.strptime(, '%Y-%m-%dT%H:%M:%S')
                # native_dt=day
                # print("native_dt", native_dt)
                # localized_dt = local_tz.localize(native_dt)
                # print("localized_dt", localized_dt)
                attendance_utc_dt = datetime.strptime(local_day_start.astimezone(utc).strftime('%Y-%m-%d %H:%M:%S'),
                                                      '%Y-%m-%d %H:%M:%S')
                print("attendance_utc_dt", attendance_utc_dt)
                technical_attendances_vals.append({
                    'check_in': attendance_utc_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'check_out': (attendance_utc_dt + relativedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'in_mode': 'technical',
                    'out_mode': 'technical',
                    'employee_id': emp.id
                })

            technical_attendances = self.env['hr.attendance'].create(technical_attendances_vals)
            print("technical_attendances", technical_attendances.mapped("check_in"))
            self.detect_is_timeoff(technical_attendances)
            # self._is_time_off_approved(technical_attendances)
            self.detect_absence_state(technical_attendances)
            to_unlink = technical_attendances.filtered(lambda a: a.overtime_hours == 0)

            body = _('This attendance was automatically created to cover an unjustified absence on that day.')
            for technical_attendance in technical_attendances - to_unlink:
                technical_attendance.message_post(body=body)

            to_unlink.unlink()

            self.env.cr.commit()
            self.env.cr.savepoint()
            self.env.flush_all()

    @api.depends("check_in", "in_mode")
    def _calculate_first_attendance(self):
        for r in self:
            if r.in_mode == 'manual' and r.check_in:
                r.first_attendance = False
                check_in_date = r.check_in.date()
                same_check_in = self.env['hr.attendance'].search(
                    [("employee_id", "=", r.employee_id.id),
                     ('check_in', '>=', fields.datetime.combine(check_in_date, fields.datetime.min.time())),
                     ('check_in', '<=', fields.datetime.combine(check_in_date, fields.datetime.max.time())),
                     ("id", '!=', r.id)], order="check_in asc", limit=1)
                # print("same_check_in", same_check_in.check_in)
                # print("r_check_in", r.check_in)

                if len(same_check_in):
                    if same_check_in.check_in > r.check_in:
                        # print("same_check_in.check_in > r.check_in:", same_check_in.check_in > r.check_in)
                        r.first_attendance = True
                        # same_check_in.first_attendance = False
                    else:
                        # print("the other is the bigger")
                        same_check_in.first_attendance = True

                        r.first_attendance = False
                else:
                    # print("the only one")
                    r.first_attendance = True
            else:
                r.first_attendance = False
