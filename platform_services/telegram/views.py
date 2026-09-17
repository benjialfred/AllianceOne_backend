from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings
from .models import TelegramUpdateLog

class TelegramHealthView(APIView):
    """
    Health check endpoint for the Telegram integration.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        is_configured = bool(token and len(token) > 10)
        processed_updates_count = TelegramUpdateLog.objects.count()

        return Response({
            "status": "healthy",
            "service": "alliance_one_telegram",
            "configured": is_configured,
            "bot_username": "AllianceOneAIBot" if is_configured else None,
            "total_updates_processed": processed_updates_count,
            "phase": "Phase 3 - Multi-Tenant Organization Context"
        }, status=200)
