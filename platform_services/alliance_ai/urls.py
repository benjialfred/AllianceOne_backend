from django.urls import path
from .views import AskAllianceAIView, MissionAuditView, MissionConfirmView, MissionCancelView

urlpatterns = [
    path('ask/', AskAllianceAIView.as_view(), name='ai-ask'),
    path('audit/<str:plan_id>/', MissionAuditView.as_view(), name='ai-audit'),
    path('mission/<str:plan_id>/confirm/', MissionConfirmView.as_view(), name='ai-mission-confirm'),
    path('mission/<str:plan_id>/cancel/', MissionCancelView.as_view(), name='ai-mission-cancel'),
]
