# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class TaskController(http.Controller):
    
    @http.route('/task_management/info', type='json', auth='user')
    def get_task_info(self, **kwargs):
        """Get basic task management info"""
        user = request.env.user
        Task = request.env['task.management']
        
        my_tasks = Task.search_count([('user_id', '=', user.id)])
        open_tasks = Task.search_count([
            ('user_id', '=', user.id),
            ('is_closed', '=', False)
        ])
        
        return {
            'my_tasks': my_tasks,
            'open_tasks': open_tasks,
            'user_name': user.name,
        }