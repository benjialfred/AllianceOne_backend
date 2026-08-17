from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'platform_services.finance'
    label = 'enterprise_finance'
    verbose_name = 'Gestion Financière et Trésorerie'
