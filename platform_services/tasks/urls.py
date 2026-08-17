from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet, TaskMilestoneViewSet, TaskLabelViewSet,
    TaskViewSet, TaskChecklistItemViewSet, TaskDashboardKPIView
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'milestones', TaskMilestoneViewSet, basename='milestone')
router.register(r'labels', TaskLabelViewSet, basename='label')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'checklist-items', TaskChecklistItemViewSet, basename='checklist-item')

urlpatterns = [
    path('dashboard-kpis/', TaskDashboardKPIView.as_view(), name='task-dashboard-kpis'),
    path('', include(router.urls)),
]
