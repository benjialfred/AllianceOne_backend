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
                "features": ["Gestion centralisée", "Calcul automatique", "Cartes scolaires"],
                "has_free_tier": False,
                "plans": [
                    {
                        "name": "Premium",
                        "is_free": False,
                        "price_monthly": 15000,
                        "price_yearly": 102999,
                        "features": ["Toutes les fonctionnalités", "Support prioritaire"]
                    }
                ]
            },
            {
                "slug": "library",
                "name": "Bibliothèque & Archives",
                "tagline": "Gestion documentaire et prêts",
                "description": "Indexation, suivi des prêts, retards et pénalités, numérisation.",
                "category": ModuleCategory.PRODUCTIVITY,
                "accent_color": "#8b5cf6",
                "icon_name": "Book",
                "version": "1.0.0",
                "permissions": ["books:read_write", "loans:manage"],
                "features": ["Catalogue", "Suivi des prêts", "Rapports d'activité"],
                "has_free_tier": True,
                "plans": [
                    {
                        "name": "Premium",
                        "is_free": False,
                        "price_monthly": 1750,
                        "price_yearly": 20000,
                        "features": ["Livres illimités", "Rapports avancés"]
                    }
                ]
            },
            {
                "slug": "tasks",
                "name": "Gestion des tâches",
                "tagline": "Kanban, Sprints et Projets",
                "description": "Tableaux agiles, assignations, suivi du temps et collaboration.",
                "category": ModuleCategory.PRODUCTIVITY,
                "accent_color": "#ef4444",
                "icon_name": "FolderKanban",
                "version": "2.0.0",
                "permissions": ["tasks:read_write", "projects:manage"],
                "features": ["Vues Kanban", "Diagrammes de Gantt", "Notifications"],
                "has_free_tier": True,
                "plans": [
                    {
                        "name": "Étudiant",
                        "is_free": False,
                        "price_monthly": 1200,
                        "price_yearly": 12000,
                        "features": ["Tarif préférentiel (Vérification requise)"]
                    },
                    {
                        "name": "Premium",
                        "is_free": False,
                        "price_monthly": 2500,
                        "price_yearly": 17000,
                        "features": ["Projets illimités", "Collaboration en temps réel"]
                    }
                ]
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
                "features": ["Multi-entrepôts", "Méthode PMP", "Bons de commande"],
                "has_free_tier": True,
                "plans": [
                    {
                        "name": "Premium",
                        "is_free": False,
                        "price_monthly": 10000,
                        "price_yearly": 98899,
                        "features": ["Entrepôts illimités", "Alertes intelligentes"]
                    }
                ]
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
                "features": ["Comptes & caisses", "Facturation certifiée", "Tontines"],
                "has_free_tier": True,
                "plans": [
                    {
                        "name": "Premium",
                        "is_free": False,
                        "price_monthly": 12000,
                        "price_yearly": 99999,
                        "features": ["Trésorerie illimitée", "Automatisations comptables"]
                    }
                ]
            }
        ]

        for mod_data in modules:
            module, created = Module.objects.update_or_create(
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
            else:
                self.stdout.write(self.style.WARNING(f"Updated module {module.slug}"))
                # Delete old plans to avoid duplicates and re-seed
                module.plans.all().delete()

            # Seed Free Plan if applicable
            if mod_data["has_free_tier"]:
                ModulePlan.objects.create(
                    module=module,
                    name="Starter (Gratuit)",
                    is_free=True,
                    price_monthly=0,
                    price_yearly=0,
                    features=["Fonctionnalités de base avec limite de volume"]
                )
            
            # Seed Paid Plans
            for plan_data in mod_data["plans"]:
                ModulePlan.objects.create(
                    module=module,
                    name=plan_data["name"],
                    is_free=plan_data["is_free"],
                    price_monthly=plan_data["price_monthly"],
                    price_yearly=plan_data["price_yearly"],
                    features=plan_data["features"]
                )
