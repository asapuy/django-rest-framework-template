﻿"""
    Django app information and initialization
"""

from django.apps import AppConfig


class Config(AppConfig):
    name = 'logs_app'
    verbose_name = 'Central Logs'

    def ready(self):

        if not hasattr(self, 'is_started'):
            self.is_started = False

        if not self.is_started:
            # Code that needs to be ran before app start can be run here.
            pass

        self.is_started = True
