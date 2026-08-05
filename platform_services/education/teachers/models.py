from platform_services.identity.models import TenantModel
import uuid
from django.db import models
from django.conf import settings


class Teacher(TenantModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teacher_profile',
    )
    code = models.CharField(max_length=50, unique=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    sex = models.CharField(max_length=10)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    specialty = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Enseignant'
        verbose_name_plural = 'Enseignants'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"ENS-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.code})'
