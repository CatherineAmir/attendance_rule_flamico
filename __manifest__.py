# -*- coding: utf-8 -*-
{
    'name': 'Attendance Rule Flamico',
    'version': '1.0',
    'summary': 'Brief description of the module',
    'description': '''
        Detailed description of the module
    ''',
    'category': 'Uncategorized',
    'author': 'SITA-EGYPT',
    'company': 'SITA-EGYPT',
    'maintainer': 'SITA-EGYPT',
    'website': 'https://sita-eg.com',
    'depends': ['base', 'mail', 'hr_attendance', 'hr_payroll_attendance', 'hr_work_entry_contract',
                'hr_flamico', 'hr_payroll'],
    'data': [
        'security/ir.model.access.csv',

        'views/hr_contract.xml',
        'views/hr_attendance.xml',
        'views/resource_calendar.xml',
        'views/hr_payslip.xml',
        'views/attendance_log.xml',
        'wizard/absence_deduction.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
