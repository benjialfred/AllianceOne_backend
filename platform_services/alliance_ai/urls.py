from django.urls import path
from .views import AskAllianceAIView

urlpatterns = [
    path('ask/', AskAllianceAIView.as_view(), name='ai-ask'),
]
