from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'platform_services.inventory'
    verbose_name = 'Gestion des Stocks et Logistique'
