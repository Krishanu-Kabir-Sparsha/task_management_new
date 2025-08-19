# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TaskTimesheetLine(models.Model):
    _name = 'task.timesheet.line'
    _description = 'Task Time Log Entry'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Work Description',
        required=True,
        help='Brief description of work done'
    )
    
    task_id = fields.Many2one(
        'task.management',
        string='Task',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    subtask_id = fields.Many2one(
        'task.subtask',
        string='Subtask',
        domain="[('parent_task_id', '=', task_id)]",
        help='Select the specific subtask you worked on'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today
    )
    
    # Time fields with multiple input options
    unit_amount = fields.Float(
        string='Duration (Hours)',
        required=True,
        default=0.0,
        help='Time spent in decimal hours (e.g., 1.5 for 1h 30m)'
    )
    
    time_start = fields.Float(
        string='Start Time',
        help='Optional: Start time in 24h format (e.g., 14.5 for 14:30)'
    )
    
    time_end = fields.Float(
        string='End Time',
        help='Optional: End time in 24h format (e.g., 16.0 for 16:00)'
    )
    
    # Quick time entry helpers
    quick_time = fields.Selection([
        ('0.25', '15 minutes'),
        ('0.5', '30 minutes'),
        ('1', '1 hour'),
        ('1.5', '1.5 hours'),
        ('2', '2 hours'),
        ('3', '3 hours'),
        ('4', '4 hours'),
        ('8', 'Full day (8 hours)')
    ], string='Quick Entry', help='Quick time selection')
    
    # Display fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    hours_display = fields.Char(
        string='Time (HH:MM)',
        compute='_compute_hours_display',
        help='Time in HH:MM format'
    )
    
    work_summary = fields.Text(
        string='Work Summary',
        compute='_compute_work_summary',
        store=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    # Task related fields
    task_type = fields.Selection(
        related='task_id.task_type',
        string='Task Type',
        store=True
    )
    
    task_stage_id = fields.Many2one(
        related='task_id.stage_id',
        string='Task Stage',
        store=True
    )
    
    @api.depends('subtask_id', 'name', 'task_id')
    def _compute_display_name(self):
        for record in self:
            if record.subtask_id:
                record.display_name = f"[{record.task_id.name}] {record.subtask_id.name}"
            elif record.name:
                record.display_name = f"[{record.task_id.name}] {record.name}"
            else:
                record.display_name = f"[{record.task_id.name}] Time Entry"
    
    @api.depends('unit_amount')
    def _compute_hours_display(self):
        """Convert decimal hours to HH:MM format for display"""
        for record in self:
            total_minutes = int(record.unit_amount * 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            record.hours_display = f"{hours:02d}:{minutes:02d}"
    
    @api.depends('task_id', 'subtask_id', 'name', 'unit_amount')
    def _compute_work_summary(self):
        for record in self:
            parts = []
            if record.task_id:
                parts.append(f"Task: {record.task_id.name}")
            if record.subtask_id:
                parts.append(f"Subtask: {record.subtask_id.name}")
            if record.name:
                parts.append(f"Work: {record.name}")
            parts.append(f"Time: {record.hours_display}")
            record.work_summary = " | ".join(parts)
    
    @api.onchange('quick_time')
    def _onchange_quick_time(self):
        """Set unit_amount based on quick time selection"""
        if self.quick_time:
            self.unit_amount = float(self.quick_time)
    
    @api.onchange('time_start', 'time_end')
    def _onchange_time_range(self):
        """Calculate duration from start and end time"""
        if self.time_start and self.time_end:
            if self.time_end < self.time_start:
                raise ValidationError(_('End time must be after start time.'))
            duration = self.time_end - self.time_start
            self.unit_amount = duration
    
    @api.onchange('subtask_id')
    def _onchange_subtask_id(self):
        """Auto-fill date when subtask is selected"""
        for record in self:
            if record.subtask_id and record.subtask_id.deadline:
                record.date = record.subtask_id.deadline
                if not record.name:  # Also auto-fill description if empty
                    record.name = record.subtask_id.name
    
    @api.onchange('date')
    def _onchange_date(self):
        """Validate date when changed"""
        today = fields.Datetime.now().date()  # Get current date from datetime
        for record in self:
            if record.date:
                if record.subtask_id and record.subtask_id.deadline:
                    if record.date > record.subtask_id.deadline:
                        return {
                            'warning': {
                                'title': _('Warning'),
                                'message': _('The selected date is after the subtask deadline (%s)', 
                                           record.subtask_id.deadline.strftime('%Y-%m-%d'))
                            }
                        }
                elif record.date > today:
                    return {
                        'warning': {
                            'title': _('Warning'),
                            'message': _('You are selecting a future date. Time logs should typically be for past work.')
                        }
                    }


    @api.constrains('unit_amount')
    def _check_unit_amount(self):
        """Validate duration is positive and reasonable"""
        for record in self:
            if record.unit_amount <= 0:
                raise ValidationError(_('Duration must be greater than 0 hours.'))
            if record.unit_amount > 24:
                raise ValidationError(_('Duration cannot exceed 24 hours for a single day.'))
            if record.unit_amount > 12:
                # Warning for unusual durations
                if not self.env.context.get('skip_duration_warning'):
                    return {
                        'warning': {
                            'title': _('Long Duration'),
                            'message': _('You are logging more than 12 hours. Please confirm this is correct.')
                        }
                    }
    
    @api.constrains('date')
    def _check_date(self):
        """Validate time log date"""
        today = fields.Datetime.now().date()  # Get current date from datetime
        for record in self:
            # If there's a subtask, allow dates up to its deadline
            if record.subtask_id and record.subtask_id.deadline:
                if record.date > record.subtask_id.deadline:
                    raise ValidationError(_(
                        'You cannot log time after the subtask deadline (%s)',
                        record.subtask_id.deadline.strftime('%Y-%m-%d')
                    ))
            # If no subtask, use standard validation (no future dates)
            elif record.date > today:
                raise ValidationError(_('You cannot log time for future dates'))
    
    @api.model
    def create(self, vals):
        """Override create to ensure consistency"""
        # Auto-fill work description if not provided
        if not vals.get('name') and vals.get('subtask_id'):
            subtask = self.env['task.subtask'].browse(vals['subtask_id'])
            vals['name'] = f"Worked on: {subtask.name}"
        elif not vals.get('name'):
            vals['name'] = "General work"
        
        return super(TaskTimesheetLine, self).create(vals)
    
    def action_edit_time_log(self):
        """Open form view for editing"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Edit Time Log'),
            'res_model': 'task.timesheet.line',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    @api.model
    def get_weekly_summary(self, user_id=None, date_from=None, date_to=None):
        """Get weekly time summary for reporting"""
        if not user_id:
            user_id = self.env.user.id
        if not date_from:
            today = fields.Date.today()
            date_from = today - timedelta(days=today.weekday())
        if not date_to:
            date_to = date_from + timedelta(days=6)
        
        domain = [
            ('user_id', '=', user_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ]
        
        time_logs = self.search(domain)
        
        summary = {
            'total_hours': sum(time_logs.mapped('unit_amount')),
            'days_worked': len(set(time_logs.mapped('date'))),
            'tasks_worked': len(set(time_logs.mapped('task_id'))),
            'details': []
        }
        
        # Group by task
        for task in time_logs.mapped('task_id'):
            task_logs = time_logs.filtered(lambda l: l.task_id == task)
            summary['details'].append({
                'task': task.name,
                'hours': sum(task_logs.mapped('unit_amount')),
                'entries': len(task_logs)
            })
        
        return summary