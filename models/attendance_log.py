from odoo import fields, models, api


class AttendanceLog(models.Model):
    _name = 'hr.attendance.log'
    _description = 'Description'

    employee_attendance_id = fields.Char('Employee Machine ID')
    employee_id = fields.Many2one("hr.employee", 'Employee')
    punch=fields.Selection([
        ("0","In"),
        ("1","Out"),
    ] ,required=False,string='State')
    time_stamp=fields.Datetime('TimeStamp')
    machine_id=fields.Selection(selection=[

        ('192.168.1.201',"Machine 1"),
        ('192.168.1.202',"Machine 2"),
        ('192.168.1.203',"Machine 3"),
        ('192.168.1.204',"Machine 4"),
        ('192.168.1.205',"Machine 5"),
    ])

    attendance_date=fields.Date('Attendance Date',default=fields.Date.today())



    error_exist=fields.Boolean('Attendance Created',default=False)

    error_message=fields.Text('Error Message')


