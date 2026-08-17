from platform_services.identity.models import TenantModel
from django.db import models


class Student(TenantModel):
    matricule = models.CharField(max_length=50, unique=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    sex = models.CharField(max_length=10)
    date_of_birth = models.DateField()
    place_of_birth = models.CharField(max_length=150)
    photo = models.ImageField(upload_to='students/photos/', blank=True, null=True)
    LIFECYCLE_STATUS_CHOICES = (
        ('PRE_INSCRIT', 'Pré-inscrit'),
        ('ADMIS', 'Admis'),
        ('INSCRIT', 'Inscrit'),
        ('REINSCRIT', 'Réinscrit'),
        ('REDOUBLANT', 'Redoublant'),
        ('ABANDON', 'Abandon'),
        ('EXCLU', 'Exclu'),
        ('DIPLOME', 'Diplômé'),
        ('ALUMNI', 'Alumni'),
    )
    lifecycle_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='PRE_INSCRIT')
    parent_name = models.CharField(max_length=150)
    parent_phone = models.CharField(max_length=30)
    parent_address = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Élève'
        verbose_name_plural = 'Élèves'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    def save(self, *args, **kwargs):
        if not self.matricule:
            import datetime
            year = str(datetime.datetime.now().year)
            # Trouver le dernier étudiant de cette année
            last_student = Student.objects.filter(matricule__startswith=f"{year}-").order_by('-matricule').first()
            if last_student:
                try:
                    last_num = int(last_student.matricule.split('-')[1])
                    new_num = last_num + 1
                except:
                    new_num = 1
            else:
                new_num = 1
            
            # Garantir l'unicité
            candidate_matricule = f"{year}-{new_num:05d}"
            while Student.objects.filter(matricule=candidate_matricule).exists():
                new_num += 1
                candidate_matricule = f"{year}-{new_num:05d}"
                
            self.matricule = candidate_matricule
        super().save(*args, **kwargs)


class Enrollment(TenantModel):
    DECISION_CHOICES = (
        ('EN_COURS', 'En cours'),
        ('PROMU', 'Promu'),
        ('REDOUBLE', 'Redouble'),
        ('EXCLU', 'Exclu'),
        ('TRANSFERE', 'Transféré'),
        ('DIPLOME', 'Diplômé'),
        ('ABANDON', 'Abandon'),
        ('EN_ATTENTE', 'En attente'),
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    academic_year = models.ForeignKey('classes.AcademicYear', on_delete=models.PROTECT, related_name='enrollments')
    school_class = models.ForeignKey('classes.SchoolClass', on_delete=models.PROTECT, related_name='enrollments')
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default='EN_COURS')
    enrollment_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('organization', 'student', 'academic_year')
        verbose_name = 'Inscription Annuelle'
        verbose_name_plural = 'Inscriptions Annuelles'
        ordering = ('-academic_year__start_year',)

    def __str__(self):
        return f"{self.student} - {self.school_class} ({self.academic_year})"


class Attendance(TenantModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    is_absent = models.BooleanField(default=True)
    reason = models.CharField(max_length=255, blank=True)
    academic_year = models.ForeignKey('classes.AcademicYear', on_delete=models.PROTECT, related_name='attendances')
    sequence = models.CharField(max_length=10, blank=True)

    class Meta:
        unique_together = ('organization', 'student', 'date', 'sequence')
        verbose_name = 'Absence/Présence'
        verbose_name_plural = 'Absences/Présences'

    def __str__(self):
        status = "Absent" if self.is_absent else "Présent"
        return f"{self.student} - {self.date} - {status}"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Enrollment)
def create_or_update_tuition_profile(sender, instance, created, **kwargs):
    from platform_services.education.finance.models import TuitionProfile
    # Update or create tuition profile for the student and academic year
    tp, tp_created = TuitionProfile.objects.get_or_create(
        student=instance.student,
        academic_year=instance.academic_year,
        defaults={
            'organization_id': getattr(instance, 'organization_id', None),
            'total_amount': instance.school_class.tuition_fee
        }
    )
    if not tp_created and tp.total_amount != instance.school_class.tuition_fee:
        # Only update if no payments have been made? Or just update it.
        tp.total_amount = instance.school_class.tuition_fee
        tp.save(update_fields=['total_amount'])
