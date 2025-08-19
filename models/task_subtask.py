# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class TaskSubtask(models.Model):
    _name = 'task.subtask'
    _description = 'Task Subtask'
    _order = 'sequence, id'
    _rec_name = 'name'

    name = fields.Char(string='Subtask', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    parent_task_id = fields.Many2one(
        'task.management',
        string='Parent Task',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    # CHANGED: From Many2one to Many2many for multiple users
    user_ids = fields.Many2many(
        'res.users',
        'task_subtask_users_rel',
        'subtask_id',
        'user_id',
        string='Assigned to',
        domain="[('share', '=', False), ('active', '=', True)]"
    )
    
    # Keep old field for compatibility, computed from user_ids
    user_id = fields.Many2one(
        'res.users',
        string='Primary Assignee',
        compute='_compute_primary_user',
        store=True
    )
    
    is_done = fields.Boolean(
        string='Done',
        default=False
    )
    
    deadline = fields.Date(string='Deadline')
    
    description = fields.Text(string='Description')
    
    # Add parent task deadline for reference
    parent_deadline = fields.Datetime(
        related='parent_task_id.date_deadline',
        string='Task Deadline',
        readonly=True,
        store=True
    )
    
    @api.depends('user_ids')
    def _compute_primary_user(self):
        """Set first user as primary for backward compatibility"""
        for subtask in self:
            subtask.user_id = subtask.user_ids[0] if subtask.user_ids else False
    
    @api.constrains('deadline', 'parent_task_id')
    def _check_deadline_range(self):
        """Ensure subtask deadline is within parent task date range"""
        for subtask in self:
            if subtask.deadline and subtask.parent_task_id:
                parent_start = subtask.parent_task_id.date_start
                parent_deadline = subtask.parent_task_id.date_deadline

                if not parent_start or not parent_deadline:
                    continue

                # Convert all dates to date objects for comparison
                subtask_date = subtask.deadline
                parent_start_date = parent_start.date() if isinstance(parent_start, datetime) else parent_start
                parent_end_date = parent_deadline.date() if isinstance(parent_deadline, datetime) else parent_deadline
                
                if subtask_date < parent_start_date or subtask_date > parent_end_date:
                    raise ValidationError(_(
                        'Subtask deadline must be within the main task\'s date range (%s - %s)'
                    ) % (
                        parent_start_date.strftime('%Y-%m-%d'),
                        parent_end_date.strftime('%Y-%m-%d')
                    ))

    @api.onchange('deadline')
    def _onchange_deadline(self):
        """Show warning if subtask deadline is outside parent task date range"""
        if self.deadline and self.parent_task_id and self.parent_task_id.date_start and self.parent_task_id.date_deadline:
            parent_start = self.parent_task_id.date_start
            parent_deadline = self.parent_task_id.date_deadline

            # Convert to date objects for comparison
            subtask_date = self.deadline
            parent_start_date = parent_start.date() if isinstance(parent_start, datetime) else parent_start
            parent_end_date = parent_deadline.date() if isinstance(parent_deadline, datetime) else parent_deadline

            if subtask_date < parent_start_date or subtask_date > parent_end_date:
                return {
                    'warning': {
                        'title': _('Invalid Deadline'),
                        'message': _(
                            'Subtask deadline must be within the main task\'s date range (%s - %s)'
                        ) % (
                            parent_start_date.strftime('%Y-%m-%d'),
                            parent_end_date.strftime('%Y-%m-%d')
                        )
                    }
                }
    
    @api.onchange('is_done')
    def _onchange_is_done(self):
        if self.is_done and self.parent_task_id:
            # Update parent task progress
            total_subtasks = len(self.parent_task_id.subtask_ids)
            if total_subtasks > 0:
                done_subtasks = len(self.parent_task_id.subtask_ids.filtered('is_done'))
                self.parent_task_id.progress = (done_subtasks / total_subtasks) * 100
    
    def name_get(self):
        """Display subtask with assignees"""
        result = []
        for subtask in self:
            if subtask.user_ids:
                users = ', '.join(subtask.user_ids.mapped('name'))
                name = f"{subtask.name} ({users})"
            else:
                name = subtask.name
            result.append((subtask.id, name))
        return result