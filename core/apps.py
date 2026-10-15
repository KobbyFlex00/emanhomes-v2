from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from .roles import sync_staff_roles

        post_migrate.connect(sync_staff_roles, sender=self)
