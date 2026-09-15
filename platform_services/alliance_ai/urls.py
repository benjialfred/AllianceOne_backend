from django.urls import path
from .views import AskAllianceAIView, MissionAuditView

urlpatterns = [
    path('ask/', AskAllianceAIView.as_view(), name='ai-ask'),
    path('audit/<str:plan_id>/', MissionAuditView.as_view(), name='ai-audit'),
]
