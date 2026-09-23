from django.core.management.base import BaseCommand
from platform_services.alliance_modules.models import Module, ModulePlan, ModuleCategory, ModuleStatus

class Command(BaseCommand):
    help = 'Seeds the initial Marketplace Modules'

    def handle(self, *args, **kwargs):
        modules = [
            {
                "slug": "education",
                "name": "Éducation Pro",
                "tagline": "Gestion complète d'établissement scolaire",
                "description": "Inscriptions, gestion des classes, relevés & bulletins, suivi financier.",
                "category": ModuleCategory.VERTICAL,
                "accent_color": "#4f46e5",
                "icon_name": "GraduationCap",
                "version": "2.4.0",
                "permissions": ["students:read_write", "grades:publish", "finances:read_write"],
                "features": ["Gestion centralisée", "Calcul automatique", "Cartes scolaires"]
            },
            {
                "slug": "inventory",
                "name": "Stocks & Logistique WMS",
                "tagline": "Traçabilité & approvisionnement",
                "description": "Contrôle des stocks en temps réel, alertes intelligentes.",
                "category": ModuleCategory.OPERATIONS,
                "accent_color": "#0ea5e9",
                "icon_name": "Package",
                "version": "2.1.0",
                "permissions": ["products:read_write", "stock:adjust", "orders:create"],
                "features": ["Multi-entrepôts", "Méthode PMP", "Bons de commande"]
            },
            {
                "slug": "finance",
                "name": "Finances & Trésorerie",
                "tagline": "Comptes, devis/facturation",
                "description": "Vision consolidée des liquidités, facturation électronique.",
                "category": ModuleCategory.FINANCE,
                "accent_color": "#059669",
                "icon_name": "Landmark",
                "version": "2.3.1",
                "permissions": ["accounts:read_write", "transactions:execute", "invoices:issue"],
                "features": ["Comptes & caisses", "Facturation certifiée", "Tontines"]
            }
        ]

        for mod_data in modules:
            module, created = Module.objects.get_or_create(
                slug=mod_data["slug"],
                defaults={
                    "name": mod_data["name"],
                    "tagline": mod_data["tagline"],
                    "description": mod_data["description"],
                    "category": mod_data["category"],
                    "accent_color": mod_data["accent_color"],
                    "icon_name": mod_data["icon_name"],
                    "version": mod_data["version"],
                    "status": ModuleStatus.ACTIVE,
                    "permissions": mod_data["permissions"],
                    "features": mod_data["features"]
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created module {module.slug}"))
                
                # Create a Free Plan and a Premium Plan
                ModulePlan.objects.create(
                    module=module,
                    name="Starter",
                    is_free=True,
                    price_monthly=0,
                    features=["Fonctionnalités de base"]
                )
                ModulePlan.objects.create(
                    module=module,
                    name="Premium",
                    is_free=False,
                    price_monthly=25000,
                    features=["Toutes les fonctionnalités", "Support prioritaire"]
                )
            else:
                self.stdout.write(self.style.WARNING(f"Module {module.slug} already exists"))
