import uuid
from django.db import models
from platform_services.identity.models import UniversalObject, Organization, User

class DashboardLayout(UniversalObject):
    """
    Configuration d'un écran de Dashboard.
    Si organization est null, c'est le dashboard du Super Admin (Platform-level).
    Si user est défini, c'est un layout personnalisé par l'utilisateur pour cette orga.
    Sinon, c'est le layout par défaut de l'organisation.
    """
    name = models.CharField(max_length=100)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name="dashboard_layouts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="dashboard_layouts")
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"Layout: {self.name} (Org: {self.organization}, User: {self.user})"

class WidgetPlacement(UniversalObject):
    """
    Position et taille d'un widget sur un Layout spécifique.
    """
    layout = models.ForeignKey(DashboardLayout, on_delete=models.CASCADE, related_name="widgets")
    widget_id = models.CharField(max_length=100, help_text="ID frontend du composant widget (ex: 'users_stats')")
    x = models.IntegerField()
    y = models.IntegerField()
    w = models.IntegerField()
    h = models.IntegerField()
    # Configuration optionnelle spécifique au widget (JSON)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['y', 'x']

    def __str__(self):
        return f"{self.widget_id} at ({self.x}, {self.y}) [{self.w}x{self.h}]"
