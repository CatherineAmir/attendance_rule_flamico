# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
from odoo.http import Response
from datetime import datetime, timedelta
from odoo.fields import Date
from odoo.exceptions import UserError, ValidationError
from pytz import timezone, utc
import logging

_logger = logging.getLogger(__name__)
local_tz = timezone('Africa/Cairo')


class AttendanceMachineIntegration(http.Controller):
    @http.route(['/machine/attendance'], type="json", auth="public", methods=['POST'],
                csrf=False)
    def get_attendance_machine(self, **kw):
        # try:
        _logger.info('get_attendance_machine %s', kw)

        data = request.httprequest.data.decode()
        payload = json.loads(data)
        # employee = request.env['hr.employee'].sudo()
        # attendance = request.env['hr.attendance'].sudo
        if payload['attendance'] == []:
            raise UserError('No attendance data found in the request payload.')

        self.create_attendance_log(payload['attendance'])
        _logger.info('logggggggggggggggggggggggggggggggggggggggggggggggggg created %s', payload['attendance'])
        for attendance in payload['attendance']:
            request.cr.commit()
            request.cr.savepoint()
            employee_id = request.env['hr.employee'].sudo().search(
                [('attendance_machine_id', '=', attendance['user_id'])], limit=1)
            # print("employee_id",employee_id)
            if employee_id:

                naive_dt = datetime.strptime(attendance['timestamp'], '%Y-%m-%dT%H:%M:%S')
                localized_dt = local_tz.localize(naive_dt)
                attendance_utc_dt = datetime.strptime(localized_dt.astimezone(utc).strftime('%Y-%m-%d %H:%M:%S'),
                                                      '%Y-%m-%d %H:%M:%S')

                all_employee_attendance = request.env['hr.attendance'].sudo().search(
                    [('employee_id', '=', employee_id.id)], order='check_in desc')

                state = str(attendance["punch"])
                if state == "0":  # in
                    # check if I need to create a record if same timestamp is not exist or timestamp difference less than 1 min
                    _logger.info("Case In")
                    attendance_employee = all_employee_attendance.filtered(lambda emp: emp.check_in

                                                                                       and attendance_utc_dt - timedelta(
                        seconds=60) <= emp.check_in <= attendance_utc_dt + timedelta(
                        seconds=60))

                    # attendance_employee = all_employee_attendance.filtered(lambda emp: emp.check_in and (
                    #             emp.check_in == attendance_utc_dt or (emp.check_in >= attendance_utc_dt - timedelta(
                    #         seconds=60 ))))
                    # and emp.check_out <= attendance_utc_dt if emp.check_out else True
                    _logger.info("attendance_employee found")
                    if len(attendance_employee):
                        pass  # do nothing
                        _logger.info("attendance_utc_dt  %s already exist for employee %s records is %s",
                                     attendance_utc_dt,
                                     employee_id.name, attendance_employee)
                    else:
                        _logger.info("will Create , write check in")
                        attendance_no_checkout = all_employee_attendance.filtered(lambda emp: not emp.check_out)
                        if len(attendance_no_checkout):
                            # todo discussed
                            time_stamps = attendance_no_checkout.mapped('check_in')

                            _logger.info("Force Write Check In")
                            attendance_no_checkout.write(
                                {
                                    "check_in": attendance_utc_dt

                                }
                            )
                            # New Check in

                            _logger.info("attendance_no_checkout for employee %s at %s and force checkout", employee_id,
                                         attendance_utc_dt, )

                            log_records = request.env['hr.attendance.log'].sudo().search(
                                [('employee_id', '=', employee_id.id), ('time_stamp', 'in', time_stamps),
                                 ('punch', '=', "0")])
                            log_records.write({
                                'error_exist': True,
                                'error_message': "Check in not followed by check out"

                            })

                        else:
                            _logger.info("Normal Create check in")
                            try:
                                request.env['hr.attendance'].sudo().create({
                                    'employee_id': employee_id.id,
                                    'check_in': attendance_utc_dt,
                                })
                            except ValidationError as e:
                                _logger.info("Skipped create attendance of employee %s  on %s due to : %s  ",
                                             employee_id.name, attendance_utc_dt, e)

                                _logger.error(e)


                elif state == "1":  # out
                    attendance_employee = all_employee_attendance.filtered(lambda
                                                                               emp: emp.check_out and (
                            emp.check_out == attendance_utc_dt or (emp.check_out >= attendance_utc_dt - timedelta(
                        seconds=60))))

                    _logger.info("Check Out %s,%s", employee_id.name, attendance_utc_dt)
                    if len(attendance_employee):
                        # attendance_employee_2 = attendance_employee.filtered(
                        #     lambda emp: emp.check_in >= attendance_employee[-1].check_out and not emp.check_out)
                        #
                        # if len(attendance_employee_2) == 1:
                        #     _logger.info("Write Check out if in and out")
                        #     _logger.info("attendance_employee %s for employee  in case 1 attendance %s",
                        #                  attendance_employee.check_in,
                        #                  employee_id.name)
                        #     attendance_employee_2.write({
                        #         "check_out": attendance_utc_dt
                        #     })
                        #
                        # else:

                            # pass

                        _logger.info("already Exist")
                        pass

                    else:
                        attendance_no_checkout = all_employee_attendance.filtered(lambda emp: not emp.check_out)
                        print("attendance_no_checkout", attendance_no_checkout)

                        if len(attendance_no_checkout) > 1:
                            # todo
                            check_ins = attendance_no_checkout.mapped('check_in')
                            if check_ins[0].check_in > attendance_utc_dt:
                                check_ins[0].write({
                                    "check_out": attendance_utc_dt

                                })
                                log_record = request.env['hr.attendance.log'].sudo().search(
                                    [('employee_id', '=', employee_id.id), ('time_stamp', 'in', check_ins[1]),
                                     ('punch', '=', "1")])
                                log_record.write({
                                    'error_exist': True,
                                    'error_message': " Check in not followed by check out"

                                })
                                _logger.info("Multiple CheckIns without check out %s For  %s", employee_id.name,
                                             attendance_utc_dt)
                            elif check_ins[1].check_in > attendance_utc_dt:
                                check_ins[1].write({
                                    "check_out": attendance_utc_dt

                                })
                                log_record = request.env['hr.attendance.log'].sudo().search(
                                    [('employee_id', '=', employee_id.id), ('time_stamp', 'in', check_ins[0]),
                                     ('punch', '=', "1")])
                                log_record.write({
                                    'error_exist': True,
                                    'error_message': " Check in not followed by check out"

                                })
                                _logger.info("Multiple CheckIns without check out %s For  %s", employee_id.name,
                                             attendance_utc_dt)

                            else:

                                log_record = request.env['hr.attendance.log'].sudo().search(
                                    [('employee_id', '=', employee_id.id), ('time_stamp', 'in', check_ins[1]),
                                     ('punch', '=', "1")])
                                log_record.write({
                                    'error_exist': True,
                                    'error_message': " Check in not followed by check out"

                                })
                                _logger.info("Multiple CheckIns without check out %s For  %s", employee_id.name,
                                             attendance_utc_dt)
                        elif len(attendance_no_checkout) == 1:

                            _logger.info("Normal write %s", attendance_no_checkout.employee_id.name)
                            _logger.info("Normal write check in  %s", attendance_no_checkout.check_in)
                            _logger.info("Normal write check out %s", attendance_utc_dt)
                            _logger.info(
                                "attendance_utc_dt - timedelta(hours=18) <= attendance_no_checkout.check_in %s",
                                (attendance_utc_dt - timedelta(hours=18)) <= attendance_no_checkout.check_in)
                            _logger.info("attendance_utc_dt - timedelta(hours=18) %s",
                                         attendance_utc_dt - timedelta(hours=18))
                            _logger.info(" attendance_no_checkout.check_in %s", attendance_no_checkout.check_in)
                            if attendance_no_checkout.check_in <= attendance_utc_dt and (
                                    attendance_utc_dt - timedelta(hours=18)) <= attendance_no_checkout.check_in:
                                attendance_no_checkout.write({
                                    "check_out": attendance_utc_dt
                                })
                            else:
                                attendance_no_checkout.sudo().unlink()


                        else:
                            _logger.info("all_employee_attendance %s", all_employee_attendance)

                            log_record = request.env['hr.attendance.log'].sudo().search(
                                [('employee_id', '=', employee_id.id), ('time_stamp', '=', attendance_utc_dt),
                                 ('punch', '=', "1")])
                            log_record.write({
                                'error_exist': True,
                                'error_message': "Check out not effected no check in for this"

                            })

        request.env.cr.commit()
        request.env.cr.savepoint()
        request.env['hr.attendance'].sudo()._cron_absence_detection()
        return Response(json.dumps({'result': 'success', 'status_code': 202}), status=200, mimetype='application/json')

    def create_attendance_log(self, attendance_list):
        _logger.info('create_attendance_log')
        attendance_log_list = []
        for attendance in attendance_list:
            employee_id = request.env['hr.employee'].sudo().search(
                [('attendance_machine_id', '=', attendance['user_id'])], limit=1)

            naive_dt = datetime.strptime(attendance['timestamp'], '%Y-%m-%dT%H:%M:%S')
            localized_dt = local_tz.localize(naive_dt)
            attendance_utc_dt_str = localized_dt.astimezone(utc).strftime('%Y-%m-%d %H:%M:%S')
            attendance_utc_dt = datetime.strptime(attendance_utc_dt_str, '%Y-%m-%d %H:%M:%S')

            existance_log = request.env['hr.attendance.log'].sudo().search(
                [("employee_id", '=', employee_id.id), ("time_stamp", '=', attendance_utc_dt)])
            if len(existance_log) == 0:
                attendance_log_list.append({
                    'employee_id': employee_id.id if employee_id else None,
                    'employee_attendance_id': str(attendance['user_id']),
                    'punch': str(attendance['punch']) if str(attendance['punch']) in ["0", "1"] else False,
                    'machine_id': attendance['machine_ip'],
                    'time_stamp': attendance_utc_dt,
                    'attendance_date': attendance_utc_dt.date(),
                    'error_exist': False if employee_id else True,
                    'error_message': "" if employee_id else "No Employee Found",
                })

        request.env['hr.attendance.log'].sudo().create(attendance_log_list)
        request.env.cr.commit()
        request.env.cr.savepoint()

        return True