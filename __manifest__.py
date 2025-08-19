# -*- coding: utf-8 -*-
{
    'name': 'Task Management Pro',
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'sequence': 5,
    'summary': 'Advanced Task Management System with Team Collaboration',
    'description': """
Task Management Pro
===================
A comprehensive task management system with:
- Individual task management
- Team management and collaboration
- Task templates and recurrence
- Timesheet integration
- Checklist support
    """,
    'author': 'Krishanu Kabir Sparsha',
    'website': 'https://daffodilplaza.com/',
    'depends': [
        'base',
        'mail',
        'calendar',
        'portal',
        'web',
    ],
    'data': [
        'security/task_security.xml',
        'security/ir.model.access.csv',
        'data/task_stages.xml',
        'views/task_team_views.xml',
        'views/task_views.xml',
        'views/task_kanban_views.xml',
        'views/task_calendar_views.xml',
        'views/task_activity_views.xml',
        # 'views/task_template_views.xml',
        'views/task_config_settings.xml',
        'views/task_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'task_management/static/src/scss/task_management.scss',
            'task_management/static/src/js/task_widget.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/icon.png'],
    
}
