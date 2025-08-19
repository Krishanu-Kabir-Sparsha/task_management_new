# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class TaskRecurrence(models.Model):
    _name = 'task.recurrence'
    _description = 'Task Recurrence Rule'
    
    name = fields.Char(string='Recurrence Name', compute='_compute_name', store=True)
    
    # Recurrence Type
    recurrence_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom')
    ], string='Recurrence Type', default='weekly', required=True)
    
    # Interval
    interval = fields.Integer(string='Repeat Every', default=1, required=True)
    
    # Weekly specific
    mon = fields.Boolean(string='Monday')
    tue = fields.Boolean(string='Tuesday')
    wed = fields.Boolean(string='Wednesday')
    thu = fields.Boolean(string='Thursday')
    fri = fields.Boolean(string='Friday')
    sat = fields.Boolean(string='Saturday')
    sun = fields.Boolean(string='Sunday')
    
    # Monthly specific
    month_by = fields.Selection([
        ('date', 'Date of month'),
        ('day', 'Day of month')
    ], string='Monthly By', default='date')
    
    day = fields.Integer(string='Date of month', default=1)
    week_list = fields.Selection([
        ('1', 'First'),
        ('2', 'Second'),
        ('3', 'Third'),
        ('4', 'Fourth'),
        ('5', 'Fifth'),
        ('-1', 'Last')
    ], string='Week')
    
    weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], string='Weekday')
    
    # End conditions
    end_type = fields.Selection([
        ('count', 'Number of repetitions'),
        ('end_date', 'End date'),
        ('forever', 'Forever')
    ], string='End Type', default='forever')
    
    count = fields.Integer(string='Number of Repetitions', default=1)
    end_date = fields.Date(string='End Date')
    
    # Related tasks
    task_ids = fields.One2many('task.management', 'recurrence_id', string='Tasks')
    task_count = fields.Integer(string='Task Count', compute='_compute_task_count', store=True)
    
    next_recurrence_date = fields.Date(string='Next Recurrence Date', compute='_compute_next_date', store=True)
    
    @api.depends('recurrence_type', 'interval')
    def _compute_name(self):
        for rec in self:
            if rec.recurrence_type == 'daily':
                rec.name = _('Every %s day(s)') % rec.interval
            elif rec.recurrence_type == 'weekly':
                rec.name = _('Every %s week(s)') % rec.interval
            elif rec.recurrence_type == 'monthly':
                rec.name = _('Every %s month(s)') % rec.interval
            elif rec.recurrence_type == 'yearly':
                rec.name = _('Every %s year(s)') % rec.interval
            else:
                rec.name = _('Custom Recurrence')
    
    @api.depends('task_ids')
    def _compute_task_count(self):
        for rec in self:
            rec.task_count = len(rec.task_ids)
    
    @api.depends('task_ids', 'task_ids.date_deadline')
    def _compute_next_date(self):
        for rec in self:
            if rec.task_ids:
                tasks_with_deadline = rec.task_ids.filtered('date_deadline')
                if tasks_with_deadline:
                    last_task = tasks_with_deadline.sorted('date_deadline', reverse=True)[0]
                    rec.next_recurrence_date = rec._get_next_recurrence_date(last_task.date_deadline)
                else:
                    rec.next_recurrence_date = fields.Date.today()
            else:
                rec.next_recurrence_date = fields.Date.today()
    
    def _get_next_recurrence_date(self, current_date):
        """Calculate the next recurrence date based on rules"""
        if isinstance(current_date, datetime):
            current_date = current_date.date()
        
        if self.recurrence_type == 'daily':
            return current_date + timedelta(days=self.interval)
        elif self.recurrence_type == 'weekly':
            return current_date + timedelta(weeks=self.interval)
        elif self.recurrence_type == 'monthly':
            return current_date + relativedelta(months=self.interval)
        elif self.recurrence_type == 'yearly':
            return current_date + relativedelta(years=self.interval)
        
        return current_date
    
    def _should_create_next_task(self):
        """Check if next task should be created based on end conditions"""
        if self.end_type == 'forever':
            return True
        elif self.end_type == 'count':
            return len(self.task_ids) < self.count
        elif self.end_type == 'end_date':
            next_date = self.next_recurrence_date
            return next_date and next_date <= self.end_date
        return False
    
    def create_next_task(self):
        """Create the next task in the recurrence series"""
        self.ensure_one()
        if not self._should_create_next_task():
            return False
        
        # Get the last task as template
        tasks_with_deadline = self.task_ids.filtered('date_deadline')
        last_task = tasks_with_deadline.sorted('date_deadline', reverse=True)[0] if tasks_with_deadline else False
        
        if last_task:
            # Calculate new deadline
            new_deadline = self._get_next_recurrence_date(last_task.date_deadline or fields.Date.today())
            
            # Copy task with new values
            new_task = last_task.copy({
                'name': last_task.name,
                'date_deadline': new_deadline,
                'date_start': fields.Datetime.now(),
                'stage_id': self.env['task.stage'].search([('stage_type', '=', 'new')], limit=1).id,
                'recurrence_id': self.id,
                'progress': 0,
            })
            
            _logger.info('Created recurring task: %s', new_task.name)
            return new_task
        return False
    
    @api.model
    def _cron_create_recurring_tasks(self):
        """Cron job to create recurring tasks"""
        recurrences = self.search([])
        for rec in recurrences:
            if rec._should_create_next_task():
                rec.create_next_task()