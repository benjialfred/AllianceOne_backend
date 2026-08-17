from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'platform_services.tasks'
    verbose_name = 'Gestion des Tâches & Projets'
