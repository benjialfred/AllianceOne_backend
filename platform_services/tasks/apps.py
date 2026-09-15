from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'platform_services.tasks'

    def ready(self):
        from . import ai_tools
        ai_tools.register_tasks_tools()

    verbose_name = 'Gestion des Tâches & Projets'
