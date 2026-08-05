from django.conf import settings
from platform_services.identity.models import TenantModel
from django.db import models


class Sequence(models.TextChoices):
    SEQ1 = 'seq1', 'Séquence 1'
    SEQ2 = 'seq2', 'Séquence 2'
    SEQ3 = 'seq3', 'Séquence 3'
    SEQ4 = 'seq4', 'Séquence 4'
    SEQ5 = 'seq5', 'Séquence 5'
    SEQ6 = 'seq6', 'Séquence 6'


class EvaluationType(models.TextChoices):
    SEQ = 'SEQ', 'Séquentielle'
    EXAM = 'EXAM', 'Examen'
    TD = 'TD', 'TD'
    CC = 'CC', 'CC'


class Grade(TenantModel):
    student = models.ForeignKey('students.Student', on_delete=models.PROTECT, related_name='grades')
    subject = models.ForeignKey('subjects.Subject', on_delete=models.PROTECT, related_name='grades')
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.PROTECT, related_name='grades')
    sequence = models.CharField(max_length=10, choices=Sequence.choices)
    evaluation_type = models.CharField(max_length=10, choices=EvaluationType.choices, default=EvaluationType.SEQ)
    academic_year = models.ForeignKey('classes.AcademicYear', on_delete=models.PROTECT, related_name='grades')
    value = models.DecimalField(max_digits=5, decimal_places=2)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('organization', 'student', 'subject', 'sequence', 'academic_year', 'evaluation_type')
        verbose_name = 'Note'
        verbose_name_plural = 'Notes'

    def __str__(self):
        return f'{self.student} - {self.subject} - {self.evaluation_type} - {self.value}'


class GradeHistory(TenantModel):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='history')
    old_value = models.DecimalField(max_digits=5, decimal_places=2)
    new_value = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True, null=True, verbose_name="Motif de modification")
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Historique de Note'
        verbose_name_plural = 'Historiques de Notes'
        ordering = ['-changed_at']


class SequenceValidation(TenantModel):
    school_class = models.ForeignKey('classes.SchoolClass', on_delete=models.CASCADE, related_name='validations')
    academic_year = models.ForeignKey('classes.AcademicYear', on_delete=models.CASCADE, related_name='validations')
    sequence = models.CharField(max_length=10, choices=Sequence.choices)
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('organization', 'school_class', 'academic_year', 'sequence')
        verbose_name = 'Validation de Séquence'
        verbose_name_plural = 'Validations de Séquences'

    def __str__(self):
        status = "Verrouillée" if self.is_locked else "Ouverte"
        return f"{self.school_class.name} - {self.sequence} ({status})"
