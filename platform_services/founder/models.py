import uuid
from django.db import models
from platform_services.identity.models import UniversalObject, User, Organization

class FounderCV(UniversalObject):
    """
    Gestion des versions du CV du fondateur.
    Une seule version doit être active à la fois.
    """
    version = models.CharField(max_length=50, help_text="ex: 1.0, 2026-V1")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="founder_cvs/")
    is_active = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_active:
            # Désactiver tous les autres CVs si celui-ci devient actif
            FounderCV.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.version} ({'Active' if self.is_active else 'Archived'})"


class FounderActivityEvent(UniversalObject):
    """
    Suivi des interactions avec le profil du fondateur.
    """
    EVENT_TYPES = (
        ('PROFILE_CLICK', 'Profile Click'),
        ('PROFILE_VIEW', 'Profile View'),
        ('CV_CLICK', 'CV Click'),
        ('CV_VIEW', 'CV View'),
        ('CV_DOWNLOAD', 'CV Download'),
    )

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="founder_events")
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    session_id = models.CharField(max_length=255, blank=True, null=True, help_text="Identifiant de session pour les visiteurs anonymes")
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        user_display = self.user.email if self.user else f"Anonymous ({self.session_id})"
        return f"{self.event_type} by {user_display} at {self.created_at}"
