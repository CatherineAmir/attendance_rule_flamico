# -*- coding: utf-8 -*-
from odoo import api, fields, models,_
from odoo.exceptions import AccessError, UserError, ValidationError

class TimeOff(models.Model):
    """ This model represents time.off."""
    _inherit = 'hr.leave'

    def action_validate(self, check_state=True):
        current_employee = self.env.user.employee_id
        leaves = self._get_leaves_on_public_holiday()
        if leaves:
            self.message_post(body="Time of Leaves On out of working Schedule",)
            # raise ValidationError(_('The following employees are not supposed to work during that period:\n %s') % ','.join(
            #     leaves.mapped('employee_id.name')))
        if check_state and any(
                holiday.state not in ['confirm', 'validate1'] and holiday.validation_type != 'no_validation' for holiday in
                self):
            raise UserError(_('Time off request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})

        leaves_second_approver = self.env['hr.leave']
        leaves_first_approver = self.env['hr.leave']

        for leave in self:
            if leave.validation_type == 'both':
                leaves_second_approver += leave
            else:
                leaves_first_approver += leave

        leaves_second_approver.write({'second_approver_id': current_employee.id})
        leaves_first_approver.write({'first_approver_id': current_employee.id})

        self._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            self.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True