# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TaskStage(models.Model):
    _name = 'task.stage'
    _description = 'Task Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    fold = fields.Boolean(string='Folded in Kanban', default=False)
    
    stage_type = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Stage Type', default='new', required=True)
    
    description = fields.Text(string='Description')
    
    # Mail template to send when task reaches this stage
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain="[('model', '=', 'task.management')]",
        help='Email template to send when task reaches this stage'
    )
    
    # Color for kanban view
    color = fields.Integer(string='Color Index')
    
    # Allow to set if stage is final (done/cancelled)
    is_closed = fields.Boolean(
        string='Is Closing Stage',
        help='Tasks in this stage are considered as closed.'
    )
    
    # Rating template
    rating_template_id = fields.Many2one(
        'mail.template',
        string='Rating Email Template',
        domain="[('model', '=', 'task.management')]",
        help='Email template to send for rating when task is completed'
    )