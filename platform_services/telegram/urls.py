from django.urls import path
from .webhook import TelegramWebhookView
from .views import TelegramHealthView

urlpatterns = [
    path('webhook/', TelegramWebhookView.as_view(), name='telegram-webhook'),
    path('health/', TelegramHealthView.as_view(), name='telegram-health'),
]
