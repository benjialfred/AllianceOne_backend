import secrets
import logging
from datetime import timedelta
from typing import Optional, Tuple
from django.utils import timezone
from django.conf import settings
from platform_services.identity.models import Membership
from .models import TelegramIdentity, TelegramLinkCode

logger = logging.getLogger(__name__)

def generate_link_code(user, ttl_minutes: int = 10) -> TelegramLinkCode:
    """
    Generates a secure, single-use, human-readable link code for an Alliance One User.
    Default validity: 10 minutes.
    """
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    random_part = "".join(secrets.choice(alphabet) for _ in range(8))
    code = f"ALX-{random_part}"

    # Invalidate any previously unused link codes for this user to avoid stale clutter
    TelegramLinkCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())

    link_code = TelegramLinkCode.objects.create(
        user=user,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=ttl_minutes)
    )
    logger.info(f"Generated Telegram link code for user {user.email}: {code} (expires in {ttl_minutes}m)")
    return link_code

def get_deep_link(code: str, bot_username: Optional[str] = None) -> str:
    """
    Constructs the official Telegram deep link for account binding.
    Clicking this link opens the bot in Telegram and automatically passes the start parameter.
    """
    username = bot_username or "AllianceOneAIBot"
    return f"https://t.me/{username}?start={code}"

def link_telegram_account(
    telegram_user_id: int,
    telegram_chat_id: int,
    raw_code: str,
    username: str = "",
    first_name: str = "",
    last_name: str = ""
) -> Tuple[bool, str, Optional[TelegramIdentity]]:
    """
    Validates the linking code and associates the Telegram identity with the Alliance One User.
    Enforces:
    1. Code existence and exact match
    2. Single-use semantics (used_at is null)
    3. Expiration check (expires_at > now)
    4. Auto-resolution of primary active Organization
    """
    clean_code = (raw_code or "").strip()
    if clean_code.lower().startswith("/start "):
        clean_code = clean_code[7:].strip()
    elif clean_code.lower().startswith("/connect "):
        clean_code = clean_code[9:].strip()

    if not clean_code:
        return False, "Code de liaison manquant.", None

    link_code = TelegramLinkCode.objects.filter(code__iexact=clean_code).select_related('user').first()
    if not link_code:
        logger.warning(f"Failed linking attempt from Telegram user {telegram_user_id}: invalid code '{clean_code}'")
        return False, "Ce code de liaison est invalide ou inexistant.", None

    if link_code.used_at is not None:
        logger.warning(f"Replay attempt for Telegram link code '{clean_code}' by {telegram_user_id}")
        return False, "Ce code de liaison a déjà été utilisé.", None

    if link_code.expires_at <= timezone.now():
        logger.warning(f"Expired code '{clean_code}' used by {telegram_user_id}")
        return False, "Ce code de liaison a expiré. Veuillez en générer un nouveau depuis votre tableau de bord.", None

    # Mark code as consumed immediately
    link_code.used_at = timezone.now()
    link_code.save(update_fields=['used_at'])

    user = link_code.user

    # Resolve default organization context for the user
    primary_membership = Membership.objects.filter(user=user).select_related('organization').first()
    active_org = primary_membership.organization if primary_membership else None

    # Update or create TelegramIdentity
    identity, created = TelegramIdentity.objects.update_or_create(
        telegram_user_id=telegram_user_id,
        defaults={
            'user': user,
            'telegram_chat_id': telegram_chat_id,
            'username': username or "",
            'first_name': first_name or "",
            'last_name': last_name or "",
            'active_organization': active_org,
            'verified_at': timezone.now(),
            'is_active': True,
        }
    )

    action_label = "created" if created else "re-linked"
    logger.info(f"Telegram account {action_label} successfully: Telegram {telegram_user_id} -> {user.email} (Org: {active_org})")

    return True, "Compte Alliance One associé avec succès !", identity

def resolve_telegram_identity(telegram_user_id: int) -> Optional[TelegramIdentity]:
    """
    Resolves an active TelegramIdentity given a Telegram user ID.
    Returns None if the account is not linked or has been deactivated.
    """
    if not telegram_user_id:
        return None
    return TelegramIdentity.objects.filter(
        telegram_user_id=telegram_user_id,
        is_active=True
    ).select_related('user', 'active_organization').first()

def unlink_telegram_account(telegram_user_id: int) -> bool:
    """
    Unlinks / deactivates the Telegram binding for the specified Telegram user ID.
    """
    identity = TelegramIdentity.objects.filter(telegram_user_id=telegram_user_id, is_active=True).first()
    if not identity:
        return False

    identity.is_active = False
    identity.save(update_fields=['is_active', 'updated_at'])
    logger.info(f"Unlinked Telegram account {telegram_user_id} from user {identity.user.email}")
    return True

def get_user_memberships(user):
    """
    Retrieves all valid Organization memberships for an Alliance One User.
    """
    return Membership.objects.filter(user=user).select_related('organization', 'role').order_by('organization__name')

def get_active_membership(identity: TelegramIdentity) -> Optional[Membership]:
    """
    Ensures server-side multi-tenant integrity.
    Verifies that the user still has an active, valid Membership in the recorded active_organization.
    If revoked or missing, transparently heals by falling back to their first valid Membership.
    """
    if not identity or not identity.user:
        return None

    # 1. Check if current active_organization still has a valid membership
    if identity.active_organization:
        membership = Membership.objects.filter(
            user=identity.user,
            organization=identity.active_organization
        ).select_related('organization', 'role').first()
        if membership:
            return membership

    # 2. Fallback / Heal: assign first available membership
    fallback_membership = get_user_memberships(identity.user).first()
    if fallback_membership:
        identity.active_organization = fallback_membership.organization
        identity.save(update_fields=['active_organization', 'updated_at'])
        logger.info(f"Auto-healed active organization for Telegram user {identity.telegram_user_id} to {fallback_membership.organization.name}")
        return fallback_membership
    else:
        # User has no memberships left
        if identity.active_organization is not None:
            identity.active_organization = None
            identity.save(update_fields=['active_organization', 'updated_at'])
        return None

def switch_active_organization(identity: TelegramIdentity, target_org_id: str) -> Tuple[bool, str, Optional[Membership]]:
    """
    Switches the active organization context for a verified Telegram user.
    Enforces strict Fail-Closed security: the user MUST possess a valid Membership
    in the requested organization. Any attempt to cross-tenant switch is rejected and logged.
    """
    if not identity or not identity.is_active:
        return False, "Compte Telegram non authentifié ou inactif.", None

    clean_org_id = str(target_org_id).strip()

    membership = Membership.objects.filter(
        user=identity.user,
        organization_id=clean_org_id
    ).select_related('organization', 'role').first()

    if not membership:
        logger.warning(
            f"SECURITY ALERT: Telegram user {identity.telegram_user_id} ({identity.user.email}) "
            f"attempted unauthorized switch to organization {clean_org_id} without membership."
        )
        return False, "Accès refusé : vous n'êtes pas membre de cette organisation.", None

    identity.active_organization = membership.organization
    identity.save(update_fields=['active_organization', 'updated_at'])
    logger.info(f"Telegram user {identity.telegram_user_id} switched active organization to '{membership.organization.name}'")

    return True, f"Organisation basculée sur {membership.organization.name} !", membership

