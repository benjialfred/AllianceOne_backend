import os
import django
import sys

sys.path.append(r"d:\projets\projets pour entreprise\Alliance One\AlliancePlatform")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alliance_platform.settings')
django.setup()

from platform_services.alliance_modules.models import Module, ModuleCategory, ModuleStatus

def seed_modules():
    modules = [
        {
            "slug": "tasks",
            "name": "Tâches & Projets",
            "tagline": "Gérez vos projets avec efficacité",
            "description": "Système complet de gestion de projets, Kanban, et suivi des tâches pour les équipes.",
            "category": ModuleCategory.PRODUCTIVITY,
            "accent_color": "#8b5cf6",
            "icon_name": "FolderKanban",
            "version": "1.0.0",
            "developer_name": "Alliance Core Team",
            "is_verified": True,
            "is_native": True,
            "status": ModuleStatus.ACTIVE,
            "permissions": ["projects.read", "projects.write", "tasks.read", "tasks.write"],
            "features": ["Tableau Kanban interactif", "Suivi du temps", "Assignation automatique", "Diagrammes de Gantt"]
        },
        {
            "slug": "library",
            "name": "Bibliothèque & CDI",
            "tagline": "Gérez vos ressources documentaires",
            "description": "Solution intégrée de gestion de bibliothèque, d'inventaire de livres et de suivi des prêts.",
            "category": ModuleCategory.VERTICAL,
            "accent_color": "#3b82f6",
            "icon_name": "Book",
            "version": "1.0.0",
            "developer_name": "Alliance Core Team",
            "is_verified": True,
            "is_native": True,
            "status": ModuleStatus.ACTIVE,
            "permissions": ["library.read", "library.write", "inventory.read"],
            "features": ["Catalogage automatique par ISBN", "Rappels de retard SMS/Email", "Réservations en ligne", "Statistiques de lecture"]
        }
    ]

    for m_data in modules:
        obj, created = Module.objects.update_or_create(
            slug=m_data['slug'],
            defaults=m_data
        )
        print(f"{'Created' if created else 'Updated'} module: {obj.name}")

if __name__ == "__main__":
    seed_modules()
