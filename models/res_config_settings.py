# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Task Management Configuration
    task_default_planned_hours = fields.Float(
        string='Default Planned Hours',
        config_parameter='task_management.default_planned_hours',
        default=8.0,
        help='Default planned hours for new tasks'
    )
    
    task_allow_timesheets = fields.Boolean(  # Keep field name unchanged
        string='Allow Time Logs on Tasks',  # Only change the label
        config_parameter='task_management.allow_timesheets',
        default=True,
        help='Allow logging time on tasks'
    )
    
    task_allow_subtasks = fields.Boolean(
        string='Allow Subtasks',
        config_parameter='task_management.allow_subtasks',
        default=True,
        help='Enable subtasks functionality'
    )
    
    task_auto_assign = fields.Boolean(
        string='Auto-assign Tasks',
        config_parameter='task_management.auto_assign',
        default=False,
        help='Automatically assign new tasks to current user'
    )
    
    task_notification_deadline = fields.Integer(
        string='Deadline Reminder (days)',
        config_parameter='task_management.notification_deadline',
        default=1,
        help='Send reminder X days before deadline'
    )