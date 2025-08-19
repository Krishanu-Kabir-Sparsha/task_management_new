# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class TaskManagement(models.Model):
    _name = 'task.management'
    _description = 'Task Management'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _rec_name = 'name'
    _order = 'priority desc, sequence, date_deadline asc, id desc'
    _check_company_auto = True

    # Basic Fields
    name = fields.Char(
        string='Task Title',
        required=True,
        tracking=True,
        index=True,
        help='Enter the task title'
    )
    
    description = fields.Html(
        string='Description',
        sanitize=True,
        help='Detailed description of the task with rich text formatting'
    )
    
    active = fields.Boolean(default=True, string='Active')
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Integer(string='Color Index', default=0)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Task Type - to distinguish between individual and team tasks
    task_type = fields.Selection([
        ('individual', 'Individual Task'),
        ('team', 'Team Task')
    ], string='Task Type', default='individual', required=True, tracking=True)
    
    # User Assignment Fields
    user_id = fields.Many2one(
        'res.users',
        string='Assigned to',
        default=lambda self: self.env.user if self.env.context.get('default_task_type') != 'team' else False,
        tracking=True,
        domain="[('share', '=', False), ('active', '=', True)]",
        index=True
    )
    
    # Team field - for team tasks
    team_id = fields.Many2one(
        'task.team',
        string='Team',
        ondelete='cascade',
        tracking=True
    )
    
    # Additional collaborators (using team_ids for compatibility)
    team_ids = fields.Many2many(
        'res.users',
        'task_team_users_rel',
        'task_id',
        'user_id',
        string='Additional Collaborators',
        domain="[('share', '=', False), ('active', '=', True)]",
        help='Additional users who can access this task'
    )
    
    # Stage and State Management
    stage_id = fields.Many2one(
        'task.stage',
        string='Stage',
        tracking=True,
        index=True,
        copy=False,
        group_expand='_read_group_stage_ids',
        default=lambda self: self._get_default_stage_id()
    )
    
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready'),
        ('blocked', 'Blocked')
    ], string='Kanban State', default='normal', tracking=True)
    
    # Priority and Tags
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='1', tracking=True, index=True)
    
    tag_ids = fields.Many2many(
        'task.tag',
        'task_tags_rel',
        'task_id',
        'tag_id',
        string='Tags',
        help='Classify and filter tasks using tags'
    )
    
    # Date Fields
    date_deadline = fields.Datetime(
        string='Deadline',
        tracking=True,
        index=True,
        help='Deadline for task completion'
    )
    
    date_start = fields.Datetime(
        string='Start Date',
        default=fields.Datetime.now,
        tracking=True,
        help='Task start date and time'
    )
    
    date_end = fields.Datetime(
        string='End Date',
        tracking=True,
        help='Task completion date and time'
    )
    
    date_assign = fields.Datetime(
        string='Assignment Date',
        tracking=True,
        help='Date when task was last assigned'
    )
    
    # Progress and Time Tracking
    progress = fields.Float(
        string='Progress (%)',
        default=0.0,
        group_operator='avg',
        tracking=True,
        help='Task completion progress from 0 to 100'
    )
    
    planned_hours = fields.Float(
        string='Planned Hours',
        tracking=True,
        help='Estimated time to complete the task'
    )
    
    effective_hours = fields.Float(
        string='Hours Spent',
        compute='_compute_effective_hours',
        store=True,
        help='Total time spent on this task'
    )
    
    remaining_hours = fields.Float(
        string='Remaining Hours',
        compute='_compute_remaining_hours',
        store=True,
        help='Remaining hours to complete the task'
    )
    
    # Time Log Fields
    timesheet_ids = fields.One2many(
        'task.timesheet.line',
        'task_id',
        string='Time Logs'  # Changed from 'Timesheets' to 'Time Logs'
    )

    allow_timesheets = fields.Boolean(
        string='Allow Time Logs',  # Changed from 'Allow Timesheets'
        default=True,
        help='Enable time log entries for this task'  # Changed help text
    )
    
    # Subtasks
    subtask_ids = fields.One2many(
        'task.subtask',
        'parent_task_id',
        string='Subtasks'
    )
    
    subtask_count = fields.Integer(
        string='Subtask Count',
        compute='_compute_subtask_count',
        store=True
    )
    
    subtask_completed_count = fields.Integer(
        string='Completed Subtasks',
        compute='_compute_subtask_count',
        store=True
    )
    
    # Parent Task (for hierarchical tasks)
    parent_id = fields.Many2one(
        'task.management',
        string='Parent Task',
        index=True
    )
    
    child_ids = fields.One2many(
        'task.management',
        'parent_id',
        string='Sub-tasks'
    )
    
    # Recurrence Fields
    recurring_task = fields.Boolean(string='Recurring Task', default=False)
    recurrence_id = fields.Many2one('task.recurrence', string='Recurrence')
    recurrence_update = fields.Selection([
        ('this', 'This task'),
        ('subsequent', 'This and following tasks'),
        ('all', 'All tasks')
    ], default='this', store=False)
    
    # Additional Information
    checklist_items = fields.Html(
        string='Checklist',
        sanitize=False,  # Disable sanitization to prevent data attribute issues
        sanitize_tags=False,  # Allow all HTML tags
        sanitize_attributes=False  # Don't sanitize attributes
    )

    notes = fields.Html(
        string='Internal Notes',
        sanitize=False,  # Disable sanitization to prevent data attribute issues
        sanitize_tags=False,  # Allow all HTML tags
        sanitize_attributes=False  # Don't sanitize attributes
    )
    
    displayed_image_id = fields.Many2one(
        'ir.attachment',
        domain="[('res_model', '=', 'task.management'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]",
        string='Cover Image'
    )
    
    # Customer/Partner
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )
    
    partner_email = fields.Char(
        string='Customer Email',
        related='partner_id.email',
        readonly=False
    )
    
    partner_phone = fields.Char(
        string='Customer Phone',
        related='partner_id.phone',
        readonly=False
    )
    
    # Template field
    template_id = fields.Many2one('task.template', string='Created from Template')
    
    # Computed Fields
    is_closed = fields.Boolean(
        string='Is Closed',
        compute='_compute_is_closed',
        store=True
    )
    
    days_to_deadline = fields.Integer(
        string='Days to Deadline',
        compute='_compute_days_to_deadline',
        store=True
    )
    
    is_user_team_task = fields.Boolean(
        string='Is User Team Task',
        compute='_compute_is_user_team_task'
    )
    
    # ========== COMPUTE METHODS ==========
    
    def _get_default_stage_id(self):
        """Get default stage for new tasks"""
        return self.env['task.stage'].search([('name', '=', 'To-Do')], limit=1)
    
    @api.depends('timesheet_ids.unit_amount')
    def _compute_effective_hours(self):
        for task in self:
            task.effective_hours = sum(task.timesheet_ids.mapped('unit_amount'))
    
    @api.depends('planned_hours', 'effective_hours')
    def _compute_remaining_hours(self):
        for task in self:
            task.remaining_hours = (task.planned_hours or 0.0) - task.effective_hours
    
    @api.depends('subtask_ids', 'subtask_ids.is_done')
    def _compute_subtask_count(self):
        for task in self:
            task.subtask_count = len(task.subtask_ids)
            task.subtask_completed_count = len(task.subtask_ids.filtered('is_done'))
    
    @api.depends('stage_id', 'stage_id.is_closed')
    def _compute_is_closed(self):
        for task in self:
            task.is_closed = task.stage_id.is_closed if task.stage_id else False
    
    @api.depends('date_deadline')
    def _compute_days_to_deadline(self):
        today = fields.Date.today()
        for task in self:
            if task.date_deadline:
                deadline_date = task.date_deadline.date() if isinstance(task.date_deadline, datetime) else task.date_deadline
                task.days_to_deadline = (deadline_date - today).days
            else:
                task.days_to_deadline = 0
    
    @api.depends('team_id', 'team_id.manager_id', 'team_id.member_ids')
    def _compute_is_user_team_task(self):
        current_user = self.env.user
        for task in self:
            if task.team_id:
                task.is_user_team_task = (
                    task.team_id.manager_id == current_user or
                    current_user in task.team_id.member_ids
                )
            else:
                task.is_user_team_task = False
    
    # ========== ONCHANGE METHODS ==========

    @api.constrains('date_start', 'date_deadline')
    def _check_date_range(self):
        """Ensure due date is not before start date"""
        for task in self:
            if task.date_start and task.date_deadline:
                if task.date_deadline < task.date_start:
                    raise ValidationError(_('Due Date/Delivery Date cannot be set before Start Date/Kickoff Date'))

    @api.onchange('date_start', 'date_deadline')
    def _onchange_date_range(self):
        """Show warning when due date is before start date"""
        if self.date_start and self.date_deadline:
            if self.date_deadline < self.date_start:
                return {
                    'warning': {
                        'title': _('Invalid Date Range'),
                        'message': _('Due Date/Delivery Date cannot be before Start Date/Kickoff Date')
                    }
                }
    
    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id:
            self.date_assign = fields.Datetime.now()
    
    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        if self.stage_id:
            # Auto-set progress based on stage
            if self.stage_id.name == 'To-Do':
                self.progress = 0
                self.kanban_state = 'normal'
            elif self.stage_id.name == 'In Progress':
                self.progress = 40
                self.kanban_state = 'normal'
            elif self.stage_id.name == 'Review':
                self.progress = 70
                self.kanban_state = 'normal'
            elif self.stage_id.name == 'Done':
                self.progress = 100
                self.date_end = fields.Datetime.now()
                self.kanban_state = 'done'
            elif self.stage_id.name == 'Cancelled':
                self.progress = 0
                self.kanban_state = 'blocked'
            
            # Set closed status
            if self.stage_id.stage_type in ['done', 'cancelled']:
                self.is_closed = True
            else:
                self.is_closed = False
    
    @api.onchange('task_type')
    def _onchange_task_type(self):
        if self.task_type == 'individual':
            self.team_id = False
            if not self.user_id:
                self.user_id = self.env.user
        elif self.task_type == 'team':
            self.user_id = False
    
    @api.onchange('team_id')
    def _onchange_team_id(self):
        if self.team_id and self.task_type != 'team':
            self.task_type = 'team'
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(TaskManagement, self).default_get(fields_list)
        # Set task type based on context
        if self.env.context.get('default_task_type'):
            defaults['task_type'] = self.env.context.get('default_task_type')
        # For individual tasks, set current user
        if defaults.get('task_type') == 'individual':
            defaults['user_id'] = self.env.user.id
        return defaults
    
    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Return all stages for kanban view grouping"""
        return self.env['task.stage'].search([])
    
    # ========== ACTION METHODS ==========
    
    def action_assign_to_me(self):
        self.write({'user_id': self.env.user.id})
    
    def action_open_parent_task(self):
        self.ensure_one()
        if not self.parent_id:
            return {}
        
        return {
            'name': _('Parent Task'),
            'type': 'ir.actions.act_window',
            'res_model': 'task.management',
            'view_mode': 'form',
            'res_id': self.parent_id.id,
        }
    
    def action_view_subtasks(self):
        self.ensure_one()
        return {
            'name': _('Subtasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'task.subtask',
            'view_mode': 'list,form',
            'domain': [('parent_task_id', '=', self.id)],
            'context': {
                'default_parent_task_id': self.id,
            }
        }
    
    def action_view_timesheets(self):
        self.ensure_one()
        return {
            'name': _('Time Logs'),  # Changed from 'Timesheets' to 'Time Logs'
            'type': 'ir.actions.act_window',
            'res_model': 'task.timesheet.line',
            'view_mode': 'list,form',
            'domain': [('task_id', '=', self.id)],
            'context': {
                'default_task_id': self.id,
                'default_user_id': self.env.user.id,
            }
        }
    
    def update_progress_from_subtasks(self):
        """Calculate progress based on completed subtasks"""
        for task in self:
            if task.subtask_ids:
                total = len(task.subtask_ids)
                done = len(task.subtask_ids.filtered('is_done'))
                task.progress = (done / total * 100) if total > 0 else 0
            else:
                # If no subtasks, calculate based on stage
                if task.stage_id.name == 'To-Do':
                    task.progress = 0
                elif task.stage_id.name == 'In Progress':
                    task.progress = 40
                elif task.stage_id.name == 'Review':
                    task.progress = 70
                elif task.stage_id.name == 'Done':
                    task.progress = 100
                elif task.stage_id.name == 'Cancelled':
                    task.progress = 0
        return True
    
    def action_open_my_tasks(self):
        """Open My Tasks view"""
        return {
            'name': 'My Tasks',
            'type': 'ir.actions.act_window',
            'res_model': 'task.management',
            'view_mode': 'list,kanban,form,calendar',
            'domain': [('task_type', '=', 'individual'), ('user_id', '=', self.env.uid)],
            'context': {
                'default_task_type': 'individual',
                'default_user_id': self.env.uid,
                'search_default_open_tasks': 1
            },
            'target': 'current',
        }

    def action_open_team_tasks(self):
        """Open Team Tasks view"""
        return {
            'name': 'Team Tasks',
            'type': 'ir.actions.act_window',
            'res_model': 'task.management',
            'view_mode': 'list,kanban,form,calendar',
            'domain': [('task_type', '=', 'team')],
            'context': {
                'default_task_type': 'team',
                'search_default_open_tasks': 1,
            },
            'target': 'current',
        }
    
    # ========== CRUD METHODS ==========
    
    @api.model
    def create(self, vals):
        # Set default values based on task type
        if vals.get('task_type') == 'individual':
            if not vals.get('user_id'):
                vals['user_id'] = self.env.user.id
        
        # Set assignment date if user is assigned
        if vals.get('user_id'):
            vals['date_assign'] = fields.Datetime.now()
        
        # Set default stage
        if not vals.get('stage_id'):
            default_stage = self.env['task.stage'].search([('name', '=', 'To-Do')], limit=1)
            if default_stage:
                vals['stage_id'] = default_stage.id
                vals['progress'] = 0
        
        task = super(TaskManagement, self).create(vals)
        
        # Auto-subscribe assigned user or team members
        if task.task_type == 'individual' and task.user_id:
            task.message_subscribe(partner_ids=[task.user_id.partner_id.id])
        elif task.task_type == 'team' and task.team_id:
            partners_to_subscribe = []
            if task.team_id.manager_id:
                partners_to_subscribe.append(task.team_id.manager_id.partner_id.id)
            if task.team_id.member_ids:
                partners_to_subscribe.extend(task.team_id.member_ids.mapped('partner_id').ids)
            if partners_to_subscribe:
                task.message_subscribe(partner_ids=partners_to_subscribe)
        
        return task
    
    def write(self, vals):
        # Track user assignment
        if 'user_id' in vals:
            vals['date_assign'] = fields.Datetime.now()
        
        result = super(TaskManagement, self).write(vals)
        
        # Subscribe new assigned user
        if 'user_id' in vals:
            for task in self:
                if task.user_id:
                    task.message_subscribe(partner_ids=[task.user_id.partner_id.id])
        
        return result
    
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _('%s (Copy)', self.name)
        return super(TaskManagement, self).copy(default)
    
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_task_as_done'):
            stage_done = self.env['task.stage'].search([('stage_type', '=', 'done')], limit=1)
            if stage_done:
                self.stage_id = stage_done
        return super(TaskManagement, self).message_post(**kwargs)
    
    def _send_overdue_notifications(self):
        """Send overdue notifications for tasks"""
        template = self.env.ref('task_management.email_template_task_overdue', raise_if_not_found=False)
        if not template:
            return
            
        for task in self:
            template.send_mail(task.id, force_send=True)
            task.message_post(
                body=_('Task is overdue. Notification sent to %s') % task.user_id.name,
                message_type='notification',
            )

    # Add these enhanced methods to TaskManagement class:

    @api.depends('planned_hours', 'effective_hours')
    def _compute_remaining_hours(self):
        """Enhanced remaining hours calculation with progress indication"""
        for task in self:
            task.remaining_hours = (task.planned_hours or 0.0) - task.effective_hours
            
            # Auto-update progress based on hours if no subtasks
            if task.planned_hours > 0 and not task.subtask_ids:
                hours_progress = min(100, (task.effective_hours / task.planned_hours) * 100)
                # Only update if significantly different from current progress
                if abs(task.progress - hours_progress) > 5:
                    task.progress = hours_progress

    def get_time_tracking_summary(self):
        """Get detailed time tracking summary for the task"""
        self.ensure_one()
        
        # Group timesheets by subtask
        subtask_times = {}
        for timesheet in self.timesheet_ids:
            subtask_key = timesheet.subtask_id.id if timesheet.subtask_id else 0
            if subtask_key not in subtask_times:
                subtask_times[subtask_key] = {
                    'name': timesheet.subtask_id.name if timesheet.subtask_id else 'Other Work',
                    'total_hours': 0,
                    'entries': []
                }
            subtask_times[subtask_key]['total_hours'] += timesheet.unit_amount
            subtask_times[subtask_key]['entries'].append({
                'date': timesheet.date,
                'user': timesheet.user_id.name,
                'hours': timesheet.unit_amount
            })
        
        return {
            'total_planned': self.planned_hours,
            'total_spent': self.effective_hours,
            'remaining': self.remaining_hours,
            'progress_percent': self.progress,
            'by_subtask': subtask_times,
            'is_over_budget': self.effective_hours > self.planned_hours if self.planned_hours else False
        }