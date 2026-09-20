import logging
from typing import Dict, Any, Optional, List, Union
from django.utils import timezone
from django.conf import settings
from .client import TelegramClient
from .models import TelegramIdentity, TelegramNotificationLog, TelegramNotificationPreference

logger = logging.getLogger(__name__)

LEVEL_EMOJIS = {
    TelegramNotificationLog.LEVEL_INFO: "ℹ️",
    TelegramNotificationLog.LEVEL_SUCCESS: "✅",
    TelegramNotificationLog.LEVEL_WARNING: "⚠️",
    TelegramNotificationLog.LEVEL_ALERT: "🚨",
}

CATEGORY_HEADERS = {
    "security": "🔒 *SÉCURITÉ & ACCÈS*",
    "finance": "💳 *FINANCES & FACTURATION*",
    "inventory": "📦 *INVENTAIRE & STOCKS*",
    "education": "🎓 *VIE SCOLAIRE & ÉTUDES*",
    "general": "🔔 *NOTIFICATION ALLIANCE ONE*",
    "system": "⚙️ *SYSTÈME & INFRASTRUCTURE*",
}


class TelegramNotificationService:
    """
    Enterprise Notification & Event Broadcasting Engine for Telegram.
    Provides idempotent, preference-aware dispatching to users, tenant organizations,
    the official channel (@allianceonechannels), and community group (@allianceonecommunity).
    """

    def __init__(self, client: Optional[TelegramClient] = None):
        self.client = client or TelegramClient()

    @staticmethod
    def _format_message(
        title: str,
        message: str,
        level: str = TelegramNotificationLog.LEVEL_INFO,
        category: str = "general",
        organization_name: Optional[str] = None
    ) -> str:
        emoji = LEVEL_EMOJIS.get(level, "🔔")
        header = CATEGORY_HEADERS.get(category.lower().strip(), f"🔔 *{category.upper()}*")
        
        parts = [
            f"{emoji} {header}",
            f"*{title}*"
        ]
        if organization_name:
            parts.append(f"_Organisation : {organization_name}_")
        
        parts.append("")
        parts.append(message)
        parts.append("")
        parts.append(f"— _Alliance One Notifications • {timezone.now().strftime('%H:%M')}_")
        return "\n".join(parts)

    @staticmethod
    def _build_action_keyboard(actions: Optional[List[Dict[str, str]]]) -> Optional[Dict[str, Any]]:
        if not actions:
            return None
        inline_keyboard: List[List[Dict[str, str]]] = []
        for act in actions:
            btn: Dict[str, str] = {"text": act.get("text", "Ouvrir")}
            if "url" in act:
                btn["url"] = act["url"]
            elif "callback_data" in act:
                btn["callback_data"] = act["callback_data"]
            else:
                btn["callback_data"] = "noop_notification"
            inline_keyboard.append([btn])
        return {"inline_keyboard": inline_keyboard}

    def send_user_notification(
        self,
        user,
        title: str,
        message: str,
        level: str = TelegramNotificationLog.LEVEL_INFO,
        category: str = "general",
        actions: Optional[List[Dict[str, str]]] = None,
        idempotency_key: Optional[str] = None,
        organization = None
    ) -> Dict[str, Any]:
        """
        Sends an alert to a specific verified user, respecting user preferences and idempotency.
        """
        if idempotency_key:
            existing = TelegramNotificationLog.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                if existing.status == TelegramNotificationLog.STATUS_DELIVERED:
                    logger.info(f"Notification with idempotency_key '{idempotency_key}' already delivered.")
                    return {
                        "status": "already_delivered",
                        "log_id": str(existing.id),
                        "idempotency_key": idempotency_key
                    }

        identity = TelegramIdentity.objects.filter(user=user, is_active=True).first()
        if not identity or not identity.telegram_chat_id:
            logger.info(f"User {getattr(user, 'email', user)} has no active Telegram identity.")
            return {"status": "skipped", "reason": "no_telegram_identity"}

        # Check user notification preferences
        pref, _ = TelegramNotificationPreference.objects.get_or_create(identity=identity)
        if not pref.is_category_enabled(category):
            logger.info(f"User {user.email} disabled notifications for category '{category}'.")
            # Log skipped
            TelegramNotificationLog.objects.create(
                recipient_type=TelegramNotificationLog.RECIPIENT_USER,
                recipient_id=str(identity.telegram_user_id),
                idempotency_key=idempotency_key,
                title=title,
                message=message,
                category=category,
                level=level,
                status=TelegramNotificationLog.STATUS_DELIVERED,
                error_message="Skipped: Category disabled in user preferences"
            )
            return {"status": "skipped", "reason": "preference_disabled"}

        org_name = organization.name if organization else (
            identity.active_organization.name if identity.active_organization else None
        )
        formatted_text = self._format_message(title, message, level=level, category=category, organization_name=org_name)
        reply_markup = self._build_action_keyboard(actions)

        log_entry = TelegramNotificationLog.objects.create(
            recipient_type=TelegramNotificationLog.RECIPIENT_USER,
            recipient_id=str(identity.telegram_user_id),
            idempotency_key=idempotency_key,
            title=title,
            message=message,
            category=category,
            level=level,
            status=TelegramNotificationLog.STATUS_PENDING
        )

        try:
            tg_res = self.client.send_message(
                chat_id=identity.telegram_chat_id,
                text=formatted_text,
                reply_markup=reply_markup
            )
            tg_msg_id = tg_res.get("message_id")
            log_entry.status = TelegramNotificationLog.STATUS_DELIVERED
            log_entry.telegram_message_id = tg_msg_id
            log_entry.sent_at = timezone.now()
            log_entry.save(update_fields=["status", "telegram_message_id", "sent_at"])
            logger.info(f"Successfully delivered notification to user {user.email} (tg_msg_id={tg_msg_id})")
            return {
                "status": "delivered",
                "log_id": str(log_entry.id),
                "telegram_message_id": tg_msg_id
            }
        except Exception as e:
            logger.error(f"Failed to deliver notification to {user.email}: {e}")
            log_entry.status = TelegramNotificationLog.STATUS_FAILED
            log_entry.error_message = str(e)
            log_entry.save(update_fields=["status", "error_message"])
            return {
                "status": "failed",
                "log_id": str(log_entry.id),
                "error": str(e)
            }

    def send_organization_alert(
        self,
        organization,
        title: str,
        message: str,
        level: str = TelegramNotificationLog.LEVEL_WARNING,
        category: str = "general",
        role_filter: Optional[List[str]] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an alert to all active verified members of an organization, optionally filtered by role names.
        """
        from platform_services.identity.models import Membership

        memberships_qs = Membership.objects.filter(organization=organization, deleted_at__isnull=True).select_related('user', 'role')
        if role_filter:
            upper_roles = [r.upper() for r in role_filter]
            memberships_qs = memberships_qs.filter(role__name__in=upper_roles)

        members = list(memberships_qs)
        sent_count = 0
        skipped_count = 0
        failed_count = 0
        results = []

        for m in members:
            user_idemp = f"{idempotency_key}_user_{m.user_id}" if idempotency_key else None
            res = self.send_user_notification(
                user=m.user,
                title=title,
                message=message,
                level=level,
                category=category,
                actions=actions,
                idempotency_key=user_idemp,
                organization=organization
            )
            results.append({"user_id": str(m.user_id), "result": res})
            if res.get("status") == "delivered":
                sent_count += 1
            elif res.get("status") in ["skipped", "already_delivered"]:
                skipped_count += 1
            else:
                failed_count += 1

        logger.info(f"Org alert '{title}' to {organization.name}: {sent_count} sent, {skipped_count} skipped, {failed_count} failed.")
        return {
            "organization_id": str(organization.id),
            "organization_name": organization.name,
            "total_candidates": len(members),
            "sent_count": sent_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "details": results
        }

    def broadcast_channel(
        self,
        title: str,
        message: str,
        channel_id: Optional[Union[str, int]] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Broadcasts an official communiqué to the Alliance One Telegram Channel (@allianceonechannels).
        """
        target_channel = channel_id or getattr(settings, 'TELEGRAM_CHANNEL_ID', '@allianceonechannels')
        if idempotency_key:
            existing = TelegramNotificationLog.objects.filter(idempotency_key=idempotency_key).first()
            if existing and existing.status == TelegramNotificationLog.STATUS_DELIVERED:
                return {"status": "already_delivered", "log_id": str(existing.id)}

        broadcast_text = (
            f"📢 *COMMUNIQUÉ OFFICIEL ALLIANCE ONE*\n\n"
            f"*{title}*\n\n"
            f"{message}\n\n"
            f"— _Canal Officiel @allianceonechannels • {timezone.now().strftime('%d/%m/%Y %H:%M')}_"
        )
        reply_markup = self._build_action_keyboard(actions)

        log_entry = TelegramNotificationLog.objects.create(
            recipient_type=TelegramNotificationLog.RECIPIENT_CHANNEL,
            recipient_id=str(target_channel),
            idempotency_key=idempotency_key,
            title=title,
            message=message,
            category="broadcast",
            level=TelegramNotificationLog.LEVEL_INFO,
            status=TelegramNotificationLog.STATUS_PENDING
        )

        try:
            tg_res = self.client.send_message(
                chat_id=target_channel,
                text=broadcast_text,
                reply_markup=reply_markup
            )
            tg_msg_id = tg_res.get("message_id")
            log_entry.status = TelegramNotificationLog.STATUS_DELIVERED
            log_entry.telegram_message_id = tg_msg_id
            log_entry.sent_at = timezone.now()
            log_entry.save(update_fields=["status", "telegram_message_id", "sent_at"])
            logger.info(f"Successfully broadcast to channel {target_channel} (msg_id={tg_msg_id})")
            return {
                "status": "delivered",
                "channel": target_channel,
                "telegram_message_id": tg_msg_id,
                "log_id": str(log_entry.id)
            }
        except Exception as e:
            logger.error(f"Failed to broadcast to channel {target_channel}: {e}")
            log_entry.status = TelegramNotificationLog.STATUS_FAILED
            log_entry.error_message = str(e)
            log_entry.save(update_fields=["status", "error_message"])
            return {
                "status": "failed",
                "channel": target_channel,
                "error": str(e),
                "log_id": str(log_entry.id)
            }

    def broadcast_community(
        self,
        title: str,
        message: str,
        group_id: Optional[Union[str, int]] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Broadcasts an announcement to the official Alliance One Community group (@allianceonecommunity).
        """
        target_group = group_id or getattr(settings, 'TELEGRAM_COMMUNITY_ID', '@allianceonecommunity')
        if idempotency_key:
            existing = TelegramNotificationLog.objects.filter(idempotency_key=idempotency_key).first()
            if existing and existing.status == TelegramNotificationLog.STATUS_DELIVERED:
                return {"status": "already_delivered", "log_id": str(existing.id)}

        community_text = (
            f"👥 *COMMUNAUTÉ ALLIANCE ONE*\n\n"
            f"*{title}*\n\n"
            f"{message}\n\n"
            f"— _Espace d'échange et d'entraide @allianceonecommunity_"
        )
        reply_markup = self._build_action_keyboard(actions)

        log_entry = TelegramNotificationLog.objects.create(
            recipient_type=TelegramNotificationLog.RECIPIENT_COMMUNITY,
            recipient_id=str(target_group),
            idempotency_key=idempotency_key,
            title=title,
            message=message,
            category="community",
            level=TelegramNotificationLog.LEVEL_INFO,
            status=TelegramNotificationLog.STATUS_PENDING
        )

        try:
            tg_res = self.client.send_message(
                chat_id=target_group,
                text=community_text,
                reply_markup=reply_markup
            )
            tg_msg_id = tg_res.get("message_id")
            log_entry.status = TelegramNotificationLog.STATUS_DELIVERED
            log_entry.telegram_message_id = tg_msg_id
            log_entry.sent_at = timezone.now()
            log_entry.save(update_fields=["status", "telegram_message_id", "sent_at"])
            logger.info(f"Successfully sent announcement to community {target_group} (msg_id={tg_msg_id})")
            return {
                "status": "delivered",
                "group": target_group,
                "telegram_message_id": tg_msg_id,
                "log_id": str(log_entry.id)
            }
        except Exception as e:
            logger.error(f"Failed to post announcement to community {target_group}: {e}")
            log_entry.status = TelegramNotificationLog.STATUS_FAILED
            log_entry.error_message = str(e)
            log_entry.save(update_fields=["status", "error_message"])
            return {
                "status": "failed",
                "group": target_group,
                "error": str(e),
                "log_id": str(log_entry.id)
            }
