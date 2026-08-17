from decimal import Decimal
from rest_framework import serializers
from .models import (
    Project, TaskMilestone, TaskLabel,
    Task, TaskChecklistItem, TaskComment, TaskTimeLog
)


class TaskLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskLabel
        fields = ['id', 'name', 'color', 'description', 'created_at']


class TaskChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskChecklistItem
        fields = ['id', 'task', 'title', 'is_completed', 'order_index', 'completed_at', 'created_at']


class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'author', 'author_name', 'content', 'created_at', 'updated_at']

    def get_author_name(self, obj):
        if obj.author:
            return getattr(obj.author, 'get_full_name', lambda: str(obj.author))() or str(obj.author.username if hasattr(obj.author, 'username') else obj.author)
        return "Utilisateur"


class TaskTimeLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = TaskTimeLog
        fields = ['id', 'task', 'user', 'user_name', 'hours', 'log_date', 'description', 'created_at']

    def get_user_name(self, obj):
        if obj.user:
            return getattr(obj.user, 'get_full_name', lambda: str(obj.user))() or str(obj.user.username if hasattr(obj.user, 'username') else obj.user)
        return "Collaborateur"


class TaskMilestoneSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_code = serializers.CharField(source='project.code', read_only=True)
    tasks_count = serializers.IntegerField(source='tasks.count', read_only=True)

    class Meta:
        model = TaskMilestone
        fields = [
            'id', 'project', 'project_name', 'project_code', 'name',
            'description', 'due_date', 'is_reached', 'reached_at',
            'tasks_count', 'created_at'
        ]


class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_code = serializers.CharField(source='project.code', read_only=True)
    project_color = serializers.CharField(source='project.color', read_only=True)
    milestone_name = serializers.CharField(source='milestone.name', read_only=True)
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    is_overdue = serializers.BooleanField(read_only=True)
    checklist_total = serializers.IntegerField(read_only=True)
    checklist_completed = serializers.IntegerField(read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)

    checklist_items = TaskChecklistItemSerializer(many=True, read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)
    time_logs = TaskTimeLogSerializer(many=True, read_only=True)
    labels_details = TaskLabelSerializer(source='labels', many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'task_number', 'title', 'description',
            'project', 'project_name', 'project_code', 'project_color',
            'milestone', 'milestone_name',
            'status', 'status_display', 'priority', 'priority_display',
            'assigned_to', 'assigned_to_name', 'created_by', 'created_by_name',
            'labels', 'labels_details',
            'start_date', 'due_date', 'completed_at',
            'estimated_hours', 'logged_hours', 'order_index',
            'is_overdue', 'checklist_total', 'checklist_completed', 'progress_percentage',
            'checklist_items', 'comments', 'time_logs',
            'created_at', 'updated_at'
        ]

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return getattr(obj.assigned_to, 'get_full_name', lambda: str(obj.assigned_to))() or str(obj.assigned_to.username if hasattr(obj.assigned_to, 'username') else obj.assigned_to)
        return "Non assigné"

    def get_created_by_name(self, obj):
        if obj.created_by:
            return getattr(obj.created_by, 'get_full_name', lambda: str(obj.created_by))() or str(obj.created_by.username if hasattr(obj.created_by, 'username') else obj.created_by)
        return "Système"


class ProjectSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    manager_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    total_tasks_count = serializers.IntegerField(read_only=True)
    completed_tasks_count = serializers.IntegerField(read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)
    milestones = TaskMilestoneSerializer(many=True, read_only=True)
    total_logged_hours = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'code', 'name', 'description', 'status', 'status_display',
            'priority', 'priority_display', 'color', 'icon',
            'start_date', 'due_date', 'budget_hours',
            'manager', 'manager_name', 'created_by', 'created_by_name',
            'total_tasks_count', 'completed_tasks_count', 'progress_percentage',
            'total_logged_hours', 'milestones', 'created_at', 'updated_at'
        ]

    def get_manager_name(self, obj):
        if obj.manager:
            return getattr(obj.manager, 'get_full_name', lambda: str(obj.manager))() or str(obj.manager.username if hasattr(obj.manager, 'username') else obj.manager)
        return "Non spécifié"

    def get_created_by_name(self, obj):
        if obj.created_by:
            return getattr(obj.created_by, 'get_full_name', lambda: str(obj.created_by))() or str(obj.created_by.username if hasattr(obj.created_by, 'username') else obj.created_by)
        return "Système"

    def get_total_logged_hours(self, obj):
        tasks = obj.tasks.all()
        total = sum((t.logged_hours for t in tasks), Decimal('0.00'))
        return total
