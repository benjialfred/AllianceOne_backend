from decimal import Decimal
from django.db.models import Q, Count, Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from platform_services.identity.mixins import TenantQuerySetMixin

from .models import (
    Project, TaskMilestone, TaskLabel,
    Task, TaskChecklistItem, TaskComment, TaskTimeLog
)
from .serializers import (
    ProjectSerializer, TaskMilestoneSerializer, TaskLabelSerializer,
    TaskSerializer, TaskChecklistItemSerializer, TaskCommentSerializer,
    TaskTimeLogSerializer
)


class ProjectViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Project.objects.prefetch_related('tasks', 'milestones').all()
    serializer_class = ProjectSerializer
    search_fields = ['code', 'name', 'description']
    filterset_fields = ['status', 'priority']

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(organization=tenant, created_by=user)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        project = self.get_object()
        tasks = project.tasks.all()
        
        status_counts = {
            'BACKLOG': tasks.filter(status='BACKLOG').count(),
            'TODO': tasks.filter(status='TODO').count(),
            'IN_PROGRESS': tasks.filter(status='IN_PROGRESS').count(),
            'IN_REVIEW': tasks.filter(status='IN_REVIEW').count(),
            'DONE': tasks.filter(status='DONE').count(),
            'BLOCKED': tasks.filter(status='BLOCKED').count(),
            'CANCELLED': tasks.filter(status='CANCELLED').count(),
        }
        
        priority_counts = {
            'LOW': tasks.filter(priority='LOW').count(),
            'MEDIUM': tasks.filter(priority='MEDIUM').count(),
            'HIGH': tasks.filter(priority='HIGH').count(),
            'URGENT': tasks.filter(priority='URGENT').count(),
        }

        overdue_count = sum(1 for t in tasks if t.is_overdue)
        total_logged = tasks.aggregate(Sum('logged_hours'))['logged_hours__sum'] or Decimal('0.00')

        return Response({
            'project_id': project.id,
            'total_tasks': tasks.count(),
            'completed_tasks': status_counts['DONE'],
            'progress_percentage': project.progress_percentage,
            'overdue_tasks': overdue_count,
            'status_breakdown': status_counts,
            'priority_breakdown': priority_counts,
            'logged_hours': total_logged,
            'budget_hours': project.budget_hours
        })


class TaskMilestoneViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = TaskMilestone.objects.select_related('project').all()
    serializer_class = TaskMilestoneSerializer
    search_fields = ['name', 'description']
    filterset_fields = ['project', 'is_reached']

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(organization=tenant)


class TaskLabelViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = TaskLabel.objects.all()
    serializer_class = TaskLabelSerializer
    search_fields = ['name', 'description']

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(organization=tenant)


class TaskViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Task.objects.select_related('project', 'milestone', 'assigned_to', 'created_by')\
                           .prefetch_related('labels', 'checklist_items', 'comments', 'time_logs').all()
    serializer_class = TaskSerializer
    search_fields = ['task_number', 'title', 'description']
    filterset_fields = ['project', 'milestone', 'status', 'priority', 'assigned_to']

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(organization=tenant, created_by=user)

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        task = self.get_object()
        new_status = request.data.get('status')
        new_order = request.data.get('order_index')

        valid_statuses = [choice[0] for choice in Task.STATUS_CHOICES]
        if new_status and new_status in valid_statuses:
            task.status = new_status
            if new_status == 'DONE':
                task.completed_at = timezone.now()
            else:
                task.completed_at = None

        if new_order is not None:
            try:
                task.order_index = int(new_order)
            except (ValueError, TypeError):
                pass

        task.save()
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def add_checklist_item(self, request, pk=None):
        task = self.get_object()
        tenant = getattr(request, 'tenant', None)
        title = request.data.get('title')
        if not title:
            return Response({'error': 'Le titre est obligatoire.'}, status=status.HTTP_400_BAD_REQUEST)

        order_index = task.checklist_items.count()
        item = TaskChecklistItem.objects.create(
            organization=tenant,
            task=task,
            title=title,
            order_index=order_index
        )
        return Response(TaskChecklistItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def toggle_checklist_item(self, request, pk=None):
        task = self.get_object()
        tenant = getattr(request, 'tenant', None)
        item_id = request.data.get('item_id')
        
        try:
            item = TaskChecklistItem.objects.get(id=item_id, task=task, organization=tenant)
            item.is_completed = not item.is_completed
            item.completed_at = timezone.now() if item.is_completed else None
            item.save()
            return Response(TaskChecklistItemSerializer(item).data)
        except TaskChecklistItem.DoesNotExist:
            return Response({'error': 'Élément introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        task = self.get_object()
        tenant = getattr(request, 'tenant', None)
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Le contenu du commentaire est obligatoire.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if request.user.is_authenticated else None
        comment = TaskComment.objects.create(
            organization=tenant,
            task=task,
            author=user,
            content=content
        )
        return Response(TaskCommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def log_time(self, request, pk=None):
        task = self.get_object()
        tenant = getattr(request, 'tenant', None)
        hours = request.data.get('hours')
        description = request.data.get('description', '')
        log_date = request.data.get('log_date') or timezone.now().date()

        try:
            hours_dec = Decimal(str(hours))
            if hours_dec <= Decimal('0.00'):
                raise ValueError()
        except (ValueError, TypeError):
            return Response({'error': 'Le nombre d\'heures doit être supérieur à zéro.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if request.user.is_authenticated else None
        timelog = TaskTimeLog.objects.create(
            organization=tenant,
            task=task,
            user=user,
            hours=hours_dec,
            log_date=log_date,
            description=description
        )
        return Response(TaskTimeLogSerializer(timelog).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        tenant = getattr(request, 'tenant', None)
        qs = self.get_queryset()
        if request.user.is_authenticated:
            qs = qs.filter(assigned_to=request.user)
        return Response(TaskSerializer(qs, many=True).data)


class TaskChecklistItemViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = TaskChecklistItem.objects.all()
    serializer_class = TaskChecklistItemSerializer

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(organization=tenant)


class TaskDashboardKPIView(APIView):
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        
        projects_qs = Project.objects.all()
        tasks_qs = Task.objects.all()
        if tenant:
            projects_qs = projects_qs.filter(organization=tenant)
            tasks_qs = tasks_qs.filter(organization=tenant)

        total_projects = projects_qs.count()
        active_projects = projects_qs.filter(status='ACTIVE').count()
        
        total_tasks = tasks_qs.count()
        done_tasks = tasks_qs.filter(status='DONE').count()
        in_progress_tasks = tasks_qs.filter(status='IN_PROGRESS').count()
        todo_tasks = tasks_qs.filter(status='TODO').count()
        in_review_tasks = tasks_qs.filter(status='IN_REVIEW').count()
        blocked_tasks = tasks_qs.filter(status='BLOCKED').count()
        
        completion_rate = int((done_tasks / total_tasks * 100)) if total_tasks > 0 else 0
        
        # Overdue tasks
        today = timezone.now().date()
        overdue_tasks_qs = tasks_qs.filter(due_date__lt=today).exclude(status__in=['DONE', 'CANCELLED'])
        overdue_count = overdue_tasks_qs.count()
        
        # Urgent / High priority tasks
        urgent_count = tasks_qs.filter(priority='URGENT').exclude(status__in=['DONE', 'CANCELLED']).count()
        high_count = tasks_qs.filter(priority='HIGH').exclude(status__in=['DONE', 'CANCELLED']).count()

        # Hours summary
        total_estimated = tasks_qs.aggregate(Sum('estimated_hours'))['estimated_hours__sum'] or Decimal('0.00')
        total_logged = tasks_qs.aggregate(Sum('logged_hours'))['logged_hours__sum'] or Decimal('0.00')

        # Recent activities (last 5 updated tasks)
        recent_tasks = tasks_qs.order_by('-updated_at')[:5]
        recent_tasks_data = TaskSerializer(recent_tasks, many=True).data

        # Overdue preview (top 4)
        overdue_preview_data = TaskSerializer(overdue_tasks_qs.order_by('due_date')[:4], many=True).data

        return Response({
            'total_projects': total_projects,
            'active_projects': active_projects,
            'total_tasks': total_tasks,
            'done_tasks': done_tasks,
            'in_progress_tasks': in_progress_tasks,
            'todo_tasks': todo_tasks,
            'in_review_tasks': in_review_tasks,
            'blocked_tasks': blocked_tasks,
            'completion_rate': completion_rate,
            'overdue_count': overdue_count,
            'urgent_count': urgent_count,
            'high_count': high_count,
            'total_estimated_hours': total_estimated,
            'total_logged_hours': total_logged,
            'status_distribution': {
                'TODO': todo_tasks,
                'IN_PROGRESS': in_progress_tasks,
                'IN_REVIEW': in_review_tasks,
                'DONE': done_tasks,
                'BLOCKED': blocked_tasks,
            },
            'recent_tasks': recent_tasks_data,
            'overdue_tasks': overdue_preview_data,
        })
