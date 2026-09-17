from django.urls import path
from .webhook import TelegramWebhookView
from .views import TelegramHealthView
from .web_views import TelegramLinkCodeView, TelegramStatusView, TelegramUnlinkView, TelegramSwitchOrgView

urlpatterns = [
    # Webhook for Telegram Bot API
    path('webhook/', TelegramWebhookView.as_view(), name='telegram-webhook'),

    # Public Health check endpoint
    path('health/', TelegramHealthView.as_view(), name='telegram-health'),

    # Authenticated web integration endpoints for Alliance One frontend
    path('link-code/', TelegramLinkCodeView.as_view(), name='telegram-link-code'),
    path('status/', TelegramStatusView.as_view(), name='telegram-status'),
    path('unlink/', TelegramUnlinkView.as_view(), name='telegram-unlink'),
    path('switch-org/', TelegramSwitchOrgView.as_view(), name='telegram-switch-org'),
]

