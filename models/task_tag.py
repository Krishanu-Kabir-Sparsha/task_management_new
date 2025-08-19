# -*- coding: utf-8 -*-

from odoo import models, fields, api
from random import randint


class TaskTag(models.Model):
    _name = 'task.tag'
    _description = 'Task Tags'
    _order = 'name'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color', default=_get_default_color)
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Tag name must be unique!'),
    ]