import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import TelegramIdentity, TelegramNotificationPreference
from .identity import generate_link_code, get_deep_link
from .notification_service import TelegramNotificationService
from django.conf import settings

logger = logging.getLogger(__name__)

class TelegramLinkCodeView(APIView):
    """
    Generates a secure, ephemeral link code and deep link for the authenticated user.
    Used by the Alliance One web application to initiate Telegram connection.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        link_code = generate_link_code(user, ttl_minutes=10)
        deep_link = get_deep_link(link_code.code)

        return Response({
            "status": "success",
            "code": link_code.code,
            "deep_link": deep_link,
            "expires_at": link_code.expires_at.isoformat(),
            "valid_minutes": 10
        }, status=200)


class TelegramStatusView(APIView):
    """
    Returns the current Telegram integration status for the authenticated user,
    including their notification preferences if linked.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        identity = TelegramIdentity.objects.filter(user=user, is_active=True).select_related('active_organization').first()

        if not identity:
            return Response({
                "is_linked": False,
                "telegram_user_id": None,
                "telegram_username": None,
                "verified_at": None,
                "active_organization": None,
                "preferences": None
            }, status=200)

        prefs, _ = TelegramNotificationPreference.objects.get_or_create(identity=identity)

        return Response({
            "is_linked": True,
            "telegram_user_id": identity.telegram_user_id,
            "telegram_username": identity.username,
            "first_name": identity.first_name,
            "verified_at": identity.verified_at.isoformat() if identity.verified_at else None,
            "active_organization": {
                "id": str(identity.active_organization.id),
                "name": identity.active_organization.name
            } if identity.active_organization else None,
            "preferences": {
                "alert_security": prefs.alert_security,
                "alert_finance": prefs.alert_finance,
                "alert_inventory": prefs.alert_inventory,
                "alert_education": prefs.alert_education,
                "daily_digest": prefs.daily_digest
            }
        }, status=200)


class TelegramUnlinkView(APIView):
    """
    Disconnects the authenticated user's Telegram identity.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        updated = TelegramIdentity.objects.filter(user=user, is_active=True).update(
            is_active=False,
            updated_at=timezone.now()
        )

        if updated > 0:
            logger.info(f"User {user.email} unlinked their Telegram account via web API.")
            return Response({"status": "success", "message": "Compte Telegram dissocié avec succès."}, status=200)
        else:
            return Response({"status": "noop", "message": "Aucun compte Telegram actif n'était associé."}, status=200)


class TelegramSwitchOrgView(APIView):
    """
    Allows an authenticated web user to switch their active Telegram organization context.
    Enforces strict membership verification.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        org_id = request.data.get("organization_id")
        if not org_id:
            return Response({"error": "organization_id est requis"}, status=400)

        identity = TelegramIdentity.objects.filter(user=user, is_active=True).first()
        if not identity:
            return Response({"error": "Aucun compte Telegram lié pour cet utilisateur"}, status=404)

        from .identity import switch_active_organization
        success, msg, membership = switch_active_organization(identity, org_id)
        if not success or not membership:
            return Response({"error": msg}, status=403)

        return Response({
            "status": "success",
            "message": msg,
            "active_organization": {
                "id": str(membership.organization.id),
                "name": membership.organization.name,
                "role": membership.role.name
            }
        }, status=200)


class TelegramPreferencesView(APIView):
    """
    Manages user notification preferences via REST API.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        identity = TelegramIdentity.objects.filter(user=user, is_active=True).first()
        if not identity:
            return Response({"is_linked": False, "preferences": None}, status=200)

        prefs, _ = TelegramNotificationPreference.objects.get_or_create(identity=identity)
        return Response({
            "is_linked": True,
            "preferences": {
                "alert_security": prefs.alert_security,
                "alert_finance": prefs.alert_finance,
                "alert_inventory": prefs.alert_inventory,
                "alert_education": prefs.alert_education,
                "daily_digest": prefs.daily_digest
            }
        }, status=200)

    def post(self, request):
        user = request.user
        identity = TelegramIdentity.objects.filter(user=user, is_active=True).first()
        if not identity:
            return Response({"error": "Aucun compte Telegram lié"}, status=404)

        prefs, _ = TelegramNotificationPreference.objects.get_or_create(identity=identity)
        data = request.data

        if "alert_security" in data:
            prefs.alert_security = bool(data["alert_security"])
        if "alert_finance" in data:
            prefs.alert_finance = bool(data["alert_finance"])
        if "alert_inventory" in data:
            prefs.alert_inventory = bool(data["alert_inventory"])
        if "alert_education" in data:
            prefs.alert_education = bool(data["alert_education"])
        if "daily_digest" in data:
            prefs.daily_digest = bool(data["daily_digest"])

        prefs.save()
        return Response({
            "status": "success",
            "message": "Préférences enregistrées avec succès.",
            "preferences": {
                "alert_security": prefs.alert_security,
                "alert_finance": prefs.alert_finance,
                "alert_inventory": prefs.alert_inventory,
                "alert_education": prefs.alert_education,
                "daily_digest": prefs.daily_digest
            }
        }, status=200)


class TelegramTestNotificationView(APIView):
    """
    Sends an immediate test alert to the authenticated user's Telegram.
    Allows end users to verify real-time connectivity from the web interface.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        identity = TelegramIdentity.objects.filter(user=user, is_active=True).first()
        if not identity:
            return Response({"error": "Votre compte Telegram n'est pas encore connecté."}, status=400)

        web_url = getattr(settings, 'ALLIANCE_WEB_SETTINGS_URL', 'https://allianceone-frontend.vercel.app')
        service = TelegramNotificationService()
        result = service.send_user_notification(
            user=user,
            title="Test de Connexion Réussi ! 🎉",
            message=(
                "Félicitations ! Votre compte Alliance One est parfaitement configuré pour "
                "recevoir les alertes d'activité, les rapports d'intelligence et les notifications "
                "critiques en temps réel."
            ),
            level="SUCCESS",
            category="general",
            actions=[
                {"text": "🌐 Accéder à Alliance One Web", "url": web_url}
            ]
        )

        if result.get("status") == "delivered":
            return Response({
                "status": "success",
                "message": "Notification de test envoyée avec succès sur votre Telegram !",
                "details": result
            }, status=200)
        else:
            return Response({
                "status": "error",
                "message": result.get("error", "Échec de l'envoi de la notification de test."),
                "details": result
            }, status=500)


