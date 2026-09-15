from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'platform_services.inventory'

    def ready(self):
        from . import ai_tools
        ai_tools.register_inventory_tools()

    verbose_name = 'Gestion des Stocks et Logistique'
