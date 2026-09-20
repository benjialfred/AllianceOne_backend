from django.urls import path
from .views import AskAllianceAIView, MissionAuditView, MissionConfirmView, MissionCancelView
from .conversation_views import AIConversationListView, AIConversationDetailView

urlpatterns = [
    path('ask/', AskAllianceAIView.as_view(), name='ai-ask'),
    path('conversations/', AIConversationListView.as_view(), name='ai-conversations-list'),
    path('conversations/<str:conversation_id>/', AIConversationDetailView.as_view(), name='ai-conversations-detail'),
    path('audit/<str:plan_id>/', MissionAuditView.as_view(), name='ai-audit'),
    path('mission/<str:plan_id>/confirm/', MissionConfirmView.as_view(), name='ai-mission-confirm'),
    path('mission/<str:plan_id>/cancel/', MissionCancelView.as_view(), name='ai-mission-cancel'),
]

