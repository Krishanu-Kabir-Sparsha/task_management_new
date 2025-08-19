# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TaskTeam(models.Model):
    _name = 'task.team'
    _description = 'Task Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    _rec_name = 'name'
    _parent_name = "parent_team_id"
    _parent_store = True
    
    name = fields.Char(string='Team Name', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index', default=0)
    
    # Manager
    manager_id = fields.Many2one(
        'res.users',
        string='Team Manager',
        required=True,
        tracking=True,
        domain="[('share', '=', False)]"
    )
    
    # Team Members
    member_ids = fields.Many2many(
        'res.users',
        'task_team_members_rel',
        'team_id',
        'user_id',
        string='Team Members',
        domain="[('share', '=', False)]"
    )
    
    # Parent/Child Teams with better logic
    parent_team_id = fields.Many2one(
        'task.team',
        string='Parent Team',
        ondelete='cascade',
        domain="[('id', '!=', active_id)]"
    )
    
    child_team_ids = fields.One2many(
        'task.team',
        'parent_team_id',
        string='Child Teams',
        context={'default_manager_id': manager_id}
    )
    
    parent_path = fields.Char(index=True)
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    # Description
    description = fields.Html(string='Team Description')
    
    # Tasks
    task_ids = fields.One2many(
        'task.management',
        'team_id',
        string='Team Tasks'
    )
    
    task_count = fields.Integer(
        string='Task Count',
        compute='_compute_task_count',
        store=True
    )

    child_team_count = fields.Integer(
    string='Sub Team Count',
    compute='_compute_child_team_count',
    store=True
)

    @api.depends('child_team_ids')
    def _compute_child_team_count(self):
        for team in self:
            team.child_team_count = len(team.child_team_ids)
    
    # Computed fields for hierarchy
    all_member_ids = fields.Many2many(
        'res.users',
        string='All Members (Including Sub-teams)',
        compute='_compute_all_members'
    )
    
    team_type = fields.Selection([
        ('parent', 'Parent Team'),
        ('child', 'Sub Team'),
        ('standalone', 'Standalone Team')
    ], string='Team Type', compute='_compute_team_type', store=True)
    
    @api.depends('parent_team_id', 'child_team_ids')
    def _compute_team_type(self):
        for team in self:
            if team.parent_team_id and team.child_team_ids:
                team.team_type = 'child'
            elif team.child_team_ids:
                team.team_type = 'parent'
            elif team.parent_team_id:
                team.team_type = 'child'
            else:
                team.team_type = 'standalone'
    
    @api.depends('member_ids', 'child_team_ids.member_ids')
    def _compute_all_members(self):
        for team in self:
            members = team.member_ids
            for child in team.child_team_ids:
                members |= child.all_member_ids
            team.all_member_ids = members
    
    @api.depends('task_ids')
    def _compute_task_count(self):
        for team in self:
            team.task_count = len(team.task_ids)
    
    @api.constrains('parent_team_id')
    def _check_parent_team(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive teams.'))
    
    @api.onchange('parent_team_id')
    def _onchange_parent_team(self):
        if self.parent_team_id:
            # Inherit company from parent team
            if self.parent_team_id.company_id:
                self.company_id = self.parent_team_id.company_id
            # Suggest manager from parent team's members
            if not self.manager_id and self.parent_team_id.member_ids:
                self.manager_id = self.parent_team_id.member_ids[0]
    
    def name_get(self):
        res = []
        for team in self:
            if team.parent_team_id:
                name = f"{team.parent_team_id.name} / {team.name}"
            else:
                name = team.name
            res.append((team.id, name))
        return res
    
    @api.model
    def create(self, vals):
        # Auto-add manager to members if not already included
        if 'manager_id' in vals and vals.get('manager_id'):
            if 'member_ids' in vals:
                member_commands = vals['member_ids']
                member_ids = []
                for command in member_commands:
                    if command[0] == 6:  # replace all
                        member_ids = command[2]
                    elif command[0] == 4:  # add
                        member_ids.append(command[1])
                if vals['manager_id'] not in member_ids:
                    member_ids.append(vals['manager_id'])
                    vals['member_ids'] = [(6, 0, member_ids)]
            else:
                vals['member_ids'] = [(4, vals['manager_id'])]
        
        return super(TaskTeam, self).create(vals)
    
    def write(self, vals):
        # Auto-add manager to members if changed
        if 'manager_id' in vals and vals.get('manager_id'):
            for team in self:
                if vals['manager_id'] not in team.member_ids.ids:
                    if 'member_ids' in vals:
                        # Add to existing member commands
                        vals['member_ids'].append((4, vals['manager_id']))
                    else:
                        vals['member_ids'] = [(4, vals['manager_id'])]
        
        return super(TaskTeam, self).write(vals)
    
    def action_create_task(self):
        """Create a new task for this team"""
        self.ensure_one()
        return {
            'name': _('New Team Task'),
            'type': 'ir.actions.act_window',
            'res_model': 'task.management',
            'view_mode': 'form',
            'view_id': self.env.ref('task_management.view_team_task_form').id,
            'context': {
                'default_team_id': self.id,
                'default_task_type': 'team',
            },
            'target': 'current',
        }
    
    def action_view_tasks(self):
        """View all tasks for this team"""
        self.ensure_one()
        return {
            'name': _('Team Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'task.management',
            'view_mode': 'list,kanban,form',
            'domain': [('team_id', '=', self.id)],
            'context': {
                'default_team_id': self.id,
                'default_task_type': 'team',
            }
        }
    
    def action_view_child_teams(self):
        """View child teams"""
        self.ensure_one()
        return {
            'name': _('Sub Teams'),
            'type': 'ir.actions.act_window',
            'res_model': 'task.team',
            'view_mode': 'list,form',
            'domain': [('parent_team_id', '=', self.id)],
            'context': {
                'default_parent_team_id': self.id,
                'default_company_id': self.company_id.id,
            }
        }