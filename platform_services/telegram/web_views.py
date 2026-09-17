import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import TelegramIdentity
from .identity import generate_link_code, get_deep_link

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
    Returns the current Telegram integration status for the authenticated user.
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
                "active_organization": None
            }, status=200)

        return Response({
            "is_linked": True,
            "telegram_user_id": identity.telegram_user_id,
            "telegram_username": identity.username,
            "first_name": identity.first_name,
            "verified_at": identity.verified_at.isoformat() if identity.verified_at else None,
            "active_organization": {
                "id": str(identity.active_organization.id),
                "name": identity.active_organization.name
            } if identity.active_organization else None
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

