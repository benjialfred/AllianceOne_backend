import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from platform_services.identity.models import TenantModel


class Project(TenantModel):
    STATUS_CHOICES = (
        ('PLANNING', 'En planification'),
        ('ACTIVE', 'En cours / Actif'),
        ('ON_HOLD', 'En pause'),
        ('COMPLETED', 'Terminé'),
        ('ARCHIVED', 'Archivé'),
    )

    PRIORITY_CHOICES = (
        ('LOW', 'Basse'),
        ('MEDIUM', 'Moyenne'),
        ('HIGH', 'Haute'),
        ('URGENT', 'Urgente'),
    )

    code = models.CharField(max_length=20, help_text="Code court préfixe (ex: PRJ, ERP, DEV)")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='ACTIVE')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    color = models.CharField(max_length=30, default='#3b82f6', help_text="Couleur HEX")
    icon = models.CharField(max_length=50, default='FolderKanban', blank=True)
    
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    budget_hours = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_projects'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_projects'
    )

    class Meta:
        verbose_name = "Projet"
        verbose_name_plural = "Projets"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.code}] {self.name}"

    @property
    def total_tasks_count(self):
        return self.tasks.count()

    @property
    def completed_tasks_count(self):
        return self.tasks.filter(status='DONE').count()

    @property
    def progress_percentage(self):
        total = self.total_tasks_count
        if total == 0:
            return 0
        return int((self.completed_tasks_count / total) * 100)


class TaskMilestone(TenantModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField(null=True, blank=True)
    is_reached = models.BooleanField(default=False)
    reached_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Jalon de Projet"
        verbose_name_plural = "Jalons de Projet"
        ordering = ['due_date', 'created_at']

    def __str__(self):
        return f"{self.project.name} - {self.name}"


class TaskLabel(TenantModel):
    name = models.CharField(max_length=80)
    color = models.CharField(max_length=30, default='#6366f1')
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Étiquette de Tâche"
        verbose_name_plural = "Étiquettes de Tâches"
        ordering = ['name']

    def __str__(self):
        return self.name


class Task(TenantModel):
    STATUS_CHOICES = (
        ('BACKLOG', 'Backlog'),
        ('TODO', 'À faire'),
        ('IN_PROGRESS', 'En cours'),
        ('IN_REVIEW', 'En révision'),
        ('DONE', 'Terminé'),
        ('BLOCKED', 'Bloqué'),
        ('CANCELLED', 'Annulé'),
    )

    PRIORITY_CHOICES = (
        ('LOW', 'Basse'),
        ('MEDIUM', 'Moyenne'),
        ('HIGH', 'Haute'),
        ('URGENT', 'Urgente'),
    )

    task_number = models.CharField(max_length=60, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks',
        null=True,
        blank=True
    )
    milestone = models.ForeignKey(
        TaskMilestone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='TODO')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks'
    )

    labels = models.ManyToManyField(TaskLabel, blank=True, related_name='tasks')

    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    estimated_hours = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.00'))
    logged_hours = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.00'))
    order_index = models.IntegerField(default=0, help_text="Ordre d'affichage dans la colonne Kanban")

    class Meta:
        verbose_name = "Tâche"
        verbose_name_plural = "Tâches"
        ordering = ['order_index', '-created_at']

    def save(self, *args, **kwargs):
        if not self.task_number:
            prefix = self.project.code.upper() if self.project and self.project.code else "TASK"
            count = Task.objects.filter(project=self.project, organization=self.organization).count() + 1
            self.task_number = f"{prefix}-{count:03d}"
            
        if self.status == 'DONE' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'DONE' and self.completed_at:
            self.completed_at = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task_number} - {self.title}"

    @property
    def is_overdue(self):
        if self.due_date and self.status not in ['DONE', 'CANCELLED']:
            return self.due_date < timezone.now().date()
        return False

    @property
    def checklist_total(self):
        return self.checklist_items.count()

    @property
    def checklist_completed(self):
        return self.checklist_items.filter(is_completed=True).count()

    @property
    def progress_percentage(self):
        if self.status == 'DONE':
            return 100
        total = self.checklist_total
        if total == 0:
            return 0 if self.status == 'TODO' or self.status == 'BACKLOG' else 50
        return int((self.checklist_completed / total) * 100)


class TaskChecklistItem(TenantModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='checklist_items')
    title = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    order_index = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Élément de Checklist"
        verbose_name_plural = "Éléments de Checklist"
        ordering = ['order_index', 'created_at']

    def __str__(self):
        return f"{self.task.task_number} - {self.title} ({'✓' if self.is_completed else '○'})"


class TaskComment(TenantModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()

    class Meta:
        verbose_name = "Commentaire de Tâche"
        verbose_name_plural = "Commentaires de Tâches"
        ordering = ['created_at']

    def __str__(self):
        return f"Commentaire de {self.author} sur {self.task.task_number}"


class TaskTimeLog(TenantModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='time_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    hours = models.DecimalField(max_digits=6, decimal_places=2)
    log_date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Saisie de Temps"
        verbose_name_plural = "Saisies de Temps"
        ordering = ['-log_date', '-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Recalculate logged hours on task
        total = self.task.time_logs.aggregate(models.Sum('hours'))['hours__sum'] or Decimal('0.00')
        self.task.logged_hours = total
        self.task.save(update_fields=['logged_hours'])
