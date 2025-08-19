# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TaskTemplate(models.Model):
    _name = 'task.template'
    _description = 'Task Template'
    _order = 'sequence, name'
    
    name = fields.Char(string='Template Name', required=True)
    description = fields.Html(string='Description Template')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    
    # Template Fields
    planned_hours = fields.Float(string='Default Planned Hours')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Default Priority', default='1')
    
    tag_ids = fields.Many2many(
        'task.tag',
        'task_template_tags_rel',
        'template_id',
        'tag_id',
        string='Default Tags'
    )
    
    user_id = fields.Many2one('res.users', string='Default Assignee')
    
    # Subtask Templates
    subtask_template_ids = fields.One2many(
        'task.subtask.template',
        'template_id',
        string='Subtask Templates'
    )
    
    # Checklist Template
    checklist_template = fields.Text(string='Checklist Template')
    
    # Usage tracking
    usage_count = fields.Integer(string='Times Used', compute='_compute_usage_count')
    last_used_date = fields.Datetime(string='Last Used', readonly=True)
    
    def _compute_usage_count(self):
        for template in self:
            template.usage_count = self.env['task.management'].search_count([
                ('template_id', '=', template.id)
            ])
    
    def action_use_template(self):
        """Create a new task from this template"""
        self.ensure_one()
        
        # Create the task
        task_vals = {
            'name': self.name,
            'description': self.description,
            'planned_hours': self.planned_hours,
            'priority': self.priority,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'user_id': self.user_id.id if self.user_id else self.env.user.id,
            'template_id': self.id,
        }
        
        new_task = self.env['task.management'].create(task_vals)
        
        # Create subtasks from template
        for subtask_template in self.subtask_template_ids:
            self.env['task.subtask'].create({
                'name': subtask_template.name,
                'parent_task_id': new_task.id,
                'sequence': subtask_template.sequence,
                'description': subtask_template.description,
            })
        
        # Update last used date
        self.last_used_date = fields.Datetime.now()
        
        # Return action to open the new task
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'task.management',
            'res_id': new_task.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_tasks(self):
        """View all tasks created from this template"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tasks from Template'),
            'res_model': 'task.management',
            'view_mode': 'list,form',
            'domain': [('template_id', '=', self.id)],
            'context': {
                'default_template_id': self.id,
            }
        }


class TaskSubtaskTemplate(models.Model):
    _name = 'task.subtask.template'
    _description = 'Task Subtask Template'
    _order = 'sequence, id'
    
    name = fields.Char(string='Subtask Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    template_id = fields.Many2one('task.template', string='Template', required=True, ondelete='cascade')