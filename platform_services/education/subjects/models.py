from platform_services.identity.models import TenantModel
import uuid
from django.db import models


class Subject(TenantModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True, blank=True)
    coefficient = models.PositiveSmallIntegerField(default=1)
    level = models.CharField(max_length=50)
    group = models.PositiveSmallIntegerField(choices=[(1, 'Groupe 1'), (2, 'Groupe 2'), (3, 'Groupe 3')], default=1)

    class Meta:
        unique_together = ('organization', 'name', 'level')
        verbose_name = 'Matière'
        verbose_name_plural = 'Matières'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"MAT-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"
