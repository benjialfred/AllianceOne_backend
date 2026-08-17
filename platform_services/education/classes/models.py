from django.conf import settings
from platform_services.identity.models import TenantModel
from django.db import models


class AcademicYear(TenantModel):
    label = models.CharField(max_length=9)
    start_year = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('organization', 'label')
        ordering = ('-start_year',)
        verbose_name = 'Année académique'
        verbose_name_plural = 'Années académiques'

    def __str__(self):
        return self.label


class Level(TenantModel):
    name = models.CharField(max_length=50) # e.g. "6ème"
    order = models.PositiveSmallIntegerField(default=0) # for sorting
    
    class Meta:
        unique_together = ('organization', 'name')
        ordering = ('order', 'name')
        verbose_name = 'Niveau'
        verbose_name_plural = 'Niveaux'

    def __str__(self):
        return self.name

class Section(TenantModel):
    name = models.CharField(max_length=50) # e.g. "Francophone", "Scientifique"
    
    class Meta:
        unique_together = ('organization', 'name')
        verbose_name = 'Section'
        verbose_name_plural = 'Sections'

    def __str__(self):
        return self.name

class SeriesGroup(TenantModel):
    name = models.CharField(max_length=100) # e.g. "Techniques 1er cycle"
    
    class Meta:
        unique_together = ('organization', 'name')
        verbose_name = 'Groupe de Séries'
        verbose_name_plural = 'Groupes de Séries'

    def __str__(self):
        return self.name

class Series(TenantModel):
    name = models.CharField(max_length=50) # e.g. "C", "D", "TI"
    group = models.ForeignKey(SeriesGroup, on_delete=models.CASCADE, related_name='series')
    
    class Meta:
        unique_together = ('organization', 'name')
        verbose_name = 'Série'
        verbose_name_plural = 'Séries'

    def __str__(self):
        return self.name

class SchoolClass(TenantModel):
    name = models.CharField(max_length=50) # e.g. "6ème 1"
    level = models.ForeignKey(Level, on_delete=models.PROTECT, related_name='classes')
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes')
    series = models.ForeignKey(Series, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes')
    capacity = models.PositiveSmallIntegerField(default=60)
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Frais de scolarité")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name='classes')
    head_teacher = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='head_classes',
    )
    subjects = models.ManyToManyField(
        'subjects.Subject',
        blank=True,
        related_name='classes'
    )

    class Meta:
        unique_together = ('organization', 'name', 'academic_year')
        verbose_name = 'Classe'
        verbose_name_plural = 'Classes'

    def __str__(self):
        return self.name

class AcademicEvent(TenantModel):
    EVENT_TYPE_CHOICES = (
        ('RENTREE', 'Rentrée'),
        ('VACANCES', 'Vacances'),
        ('FERIE', 'Jour férié'),
        ('EXAMEN', 'Examen'),
        ('EVALUATION', 'Évaluation'),
        ('CONSEIL', 'Conseil de classe'),
        ('REUNION_PROF', 'Réunion enseignants'),
        ('REUNION_PARENTS', 'Réunion parents'),
        ('CULTUREL', 'Journée culturelle'),
        ('SPORT', 'Journée sportive'),
        ('SORTIE', 'Sortie pédagogique'),
        ('FORMATION', 'Formation'),
        ('FERMETURE', 'Fermeture exceptionnelle'),
        ('CEREMONIE', 'Cérémonie'),
        ('SOUTENANCE', 'Soutenance'),
        ('CONCOURS', 'Concours'),
        ('ORIENTATION', 'Orientation'),
        ('INSCRIPTION', 'Inscription'),
        ('REINSCRIPTION', 'Réinscription'),
        ('REMISE_BULLETINS', 'Remise des bulletins'),
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, default='CULTUREL')
    start_date = models.DateField()
    end_date = models.DateField()
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='events')
    
    suspends_attendance = models.BooleanField(default=False)
    locks_grades = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ('-start_date',)
        verbose_name = 'Événement académique'
        verbose_name_plural = 'Événements académiques'

    def __str__(self):
        return f"{self.title} ({self.start_date} - {self.end_date})"
