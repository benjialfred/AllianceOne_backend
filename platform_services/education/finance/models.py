from django.conf import settings
from platform_services.identity.models import TenantModel
from django.db import models
from platform_services.education.students.models import Student
from platform_services.education.classes.models import AcademicYear

class TuitionProfile(TenantModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='tuition_profiles')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='tuition_profiles')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    class Meta:
        unique_together = ('organization', 'student', 'academic_year')
        verbose_name = "Profil financier"
        verbose_name_plural = "Profils financiers"

    def __str__(self):
        return f"{self.student} - {self.academic_year}"

    @property
    def total_paid(self):
        return sum(p.amount for p in self.payments.all())

    @property
    def remaining_amount(self):
        return self.total_amount - self.total_paid

class Payment(TenantModel):
    tuition_profile = models.ForeignKey(TuitionProfile, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    receipt_number = models.CharField(max_length=50, unique=True, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ('-date',)
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            import uuid
            import datetime
            year = datetime.datetime.now().year
            self.receipt_number = f"REC-{year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.receipt_number} - {self.amount}"
