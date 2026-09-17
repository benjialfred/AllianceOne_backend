import logging
from typing import Dict, Any, Optional
from .client import TelegramClient
from .keyboards import get_main_menu_keyboard, get_help_keyboard, get_community_keyboard

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = """*Bienvenue sur Alliance One* 👋
_L'écosystème unifié pour vos opérations et votre intelligence métier._

Ce bot Telegram officiel est votre *canal d'accès direct* à la plateforme Alliance One et à *Alliance AI*.

*Que souhaitez-vous faire ?*
Utilisez les boutons ci-dessous ou tapez une commande :
• /start — Revenir au menu principal
• /help — Obtenir de l'aide et la liste des commandes
• /community — Accéder à la communauté et aux canaux officiels
• /status — État de connexion de la passerelle
"""

HELP_MESSAGE = """*Centre d'Aide Alliance One* ❓

*Commandes disponibles :*
• `/start` — Affiche le message de bienvenue et le menu interactif.
• `/connect <code>` — Lie votre compte utilisateur Alliance One de manière sécurisée.
• `/me` — Affiche vos informations de compte lié et votre organisation active.
• `/community` — Liens vers notre groupe et canal officiel.
• `/status` — Vérifie l'état opérationnel de la passerelle.
• `/disconnect` — Dissocie votre compte Telegram d'Alliance One.
• `/help` — Affiche ce message d'aide.

*Fonctionnalités avancées (Phases suivantes) :*
• `/organization` — Gérer et basculer votre organisation active (Phase 3).
• `/ai` — Poser des questions et exécuter des missions avec Alliance AI (Phase 4 & 5).

Pour toute question technique, rejoignez notre groupe d'entraide !
"""

CONNECT_INFO_MESSAGE = """*Liaison de votre compte Alliance One* 🔗

Pour associer votre compte Telegram à votre compte Alliance One :

1. Connectez-vous à votre plateforme web *Alliance One*.
2. Ouvrez vos paramètres ou cliquez sur *« Connecter Telegram »*.
3. Cliquez sur le lien direct ou tapez la commande suivante ici :
   `/connect <VOTRE_CODE>`

_Chaque code est à usage unique et expire après 10 minutes pour votre sécurité._
"""

COMMUNITY_MESSAGE = """*Communauté Alliance One* 👥

Rejoignez notre réseau de professionnels, développeurs et utilisateurs :

• *📢 Canal Officiel* : Mises à jour, nouvelles versions, annonces officielles de l'écosystème.
• *👥 Groupe Communautaire* : Échanges, assistance entre pairs, retours d'expérience et discussions ouvertes.

_Sélectionnez une option ci-dessous :_
"""

STATUS_MESSAGE = """*Statut de la Passerelle Alliance One* ⚡

• *Passerelle Telegram* : En ligne ✅
• *Système central* : Opérationnel ✅
• *Architecture* : Fail-Closed & Multi-Tenant Sécurisé ✅
• *Version de l'intégration* : V2.0 (Phase 2 Identity & Account Linking)
"""

AI_INFO_MESSAGE = """*Alliance AI sur Telegram* 🤖

Alliance AI est le cerveau opérationnel d'Alliance One.
Il vous permettra bientôt de :
• Consulter l'état de vos inscriptions et classes
• Surveiller les stocks faibles et alertes
• Suivre les opérations financières
• Créer des tâches et vérifier vos indicateurs

_L'intégration d'Alliance AI sera activée dans les phases suivantes après liaison sécurisée de votre compte._
"""

from .identity import resolve_telegram_identity, link_telegram_account, unlink_telegram_account

def handle_update(update: Dict[str, Any], client: Optional[TelegramClient] = None) -> Dict[str, Any]:
    """
    Primary dispatcher for all incoming Telegram webhook updates.
    Handles messages, commands, and inline callback queries.
    """
    if client is None:
        client = TelegramClient()

    if "message" in update:
        return handle_message(update["message"], client)
    elif "callback_query" in update:
        return handle_callback_query(update["callback_query"], client)
    else:
        logger.info(f"Unhandled update type: {list(update.keys())}")
        return {"status": "ignored", "reason": "unhandled_update_type"}

def handle_message(message: Dict[str, Any], client: TelegramClient) -> Dict[str, Any]:
    """
    Routes incoming text messages and commands with identity context.
    """
    chat_id = message.get("chat", {}).get("id")
    from_user = message.get("from", {})
    user_id = from_user.get("id") or chat_id
    username = from_user.get("username") or ""
    first_name = from_user.get("first_name") or ""
    last_name = from_user.get("last_name") or ""
    text = (message.get("text") or "").strip()

    if not chat_id:
        return {"status": "ignored", "reason": "missing_chat_id"}

    # Resolve active Telegram identity for this user
    identity = resolve_telegram_identity(user_id) if user_id else None
    is_linked = identity is not None

    logger.info(f"Received Telegram message from user {user_id} (linked={is_linked}): '{text}'")

    # Command: /start (supports deep linking: /start ALX-XXXX or /start link_XXXX)
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            code_arg = parts[1].strip()
            success, msg, linked_identity = link_telegram_account(
                telegram_user_id=user_id,
                telegram_chat_id=chat_id,
                raw_code=code_arg,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            if success and linked_identity:
                org_name = linked_identity.active_organization.name if linked_identity.active_organization else "Alliance One"
                response_text = (
                    f"🎉 *Félicitations ! Votre compte Alliance One est connecté avec succès.*\n\n"
                    f"• *Utilisateur* : {linked_identity.first_name or linked_identity.user.email} (`{linked_identity.user.email}`)\n"
                    f"• *Organisation active* : *{org_name}*\n"
                    f"• *Sécurité* : Canal chiffré et authentifié ✅\n\n"
                    f"Vous pouvez maintenant utiliser les fonctionnalités de la plateforme directement depuis Telegram."
                )
                client.send_message(chat_id, response_text, reply_markup=get_main_menu_keyboard(is_linked=True))
                return {"status": "handled", "command": "/start_deep_link", "success": True}
            else:
                response_text = (
                    f"❌ *Échec de liaison de votre compte*\n\n"
                    f"{msg}\n\n"
                    f"Générez un nouveau code depuis votre espace web Alliance One ou tapez `/connect` pour obtenir de l'aide."
                )
                client.send_message(chat_id, response_text, reply_markup=get_main_menu_keyboard(is_linked=is_linked))
                return {"status": "handled", "command": "/start_deep_link", "success": False, "error": msg}

        # Regular /start
        client.send_message(chat_id, WELCOME_MESSAGE, reply_markup=get_main_menu_keyboard(is_linked=is_linked))
        return {"status": "handled", "command": "/start"}

    # Command: /connect (with optional code: /connect ALX-XXXX)
    elif text.startswith("/connect"):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            code_arg = parts[1].strip()
            success, msg, linked_identity = link_telegram_account(
                telegram_user_id=user_id,
                telegram_chat_id=chat_id,
                raw_code=code_arg,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            if success and linked_identity:
                org_name = linked_identity.active_organization.name if linked_identity.active_organization else "Alliance One"
                response_text = (
                    f"🎉 *Compte Alliance One associé avec succès !*\n\n"
                    f"• *Utilisateur* : `{linked_identity.user.email}`\n"
                    f"• *Organisation* : *{org_name}*\n"
                    f"• *Statut* : Vérifié ✅"
                )
                client.send_message(chat_id, response_text, reply_markup=get_main_menu_keyboard(is_linked=True))
                return {"status": "handled", "command": "/connect", "success": True}
            else:
                response_text = f"❌ *Erreur de liaison :* {msg}"
                client.send_message(chat_id, response_text, reply_markup=get_main_menu_keyboard(is_linked=is_linked))
                return {"status": "handled", "command": "/connect", "success": False, "error": msg}

        # /connect without arguments
        if is_linked:
            org_name = identity.active_organization.name if identity.active_organization else "Alliance One"
            response_text = (
                f"ℹ️ *Votre compte est déjà connecté*\n\n"
                f"• *Utilisateur lié* : `{identity.user.email}`\n"
                f"• *Organisation* : *{org_name}*\n\n"
                f"Tapez `/me` pour consulter vos détails ou `/disconnect` pour vous déconnecter."
            )
        else:
            response_text = CONNECT_INFO_MESSAGE
        client.send_message(chat_id, response_text, reply_markup=get_main_menu_keyboard(is_linked=is_linked))
        return {"status": "handled", "command": "/connect"}

    # Command: /me
    elif text.startswith("/me"):
        if is_linked:
            org_name = identity.active_organization.name if identity.active_organization else "Alliance One"
            verified_str = identity.verified_at.strftime('%d/%m/%Y à %H:%M') if identity.verified_at else "Actif"
            response_text = (
                f"👤 *Profil Alliance One Connecté*\n\n"
                f"• *Email* : `{identity.user.email}`\n"
                f"• *Nom* : {identity.first_name or identity.user.email}\n"
                f"• *Organisation active* : *{org_name}*\n"
                f"• *ID Telegram* : `{user_id}`\n"
                f"• *Liaison établie le* : {verified_str}\n"
                f"• *Statut* : Authentifié ✅"
            )
        else:
            response_text = (
                f"⚠️ *Compte non connecté*\n\n"
                f"Votre compte Telegram n'est pas encore associé à Alliance One.\n\n"
                f"Utilisez `/connect` ou cliquez sur le bouton ci-dessous pour associer votre compte."
            )
        client.send_message(chat_id, response_text, reply_markup=get_main_menu_keyboard(is_linked=is_linked))
        return {"status": "handled", "command": "/me", "is_linked": is_linked}

    # Command: /disconnect
    elif text.startswith("/disconnect"):
        if is_linked:
            unlink_telegram_account(user_id)
            response_text = (
                f"🚪 *Compte dissocié avec succès*\n\n"
                f"Votre compte Telegram n'est plus associé à Alliance One.\n"
                f"Pour reconnecter votre compte à tout moment, tapez `/connect`."
            )
        else:
            response_text = "ℹ️ Aucun compte Alliance One n'est actuellement associé à ce profil Telegram."
        client.send_message(chat_id, response_text, reply_markup=get_main_menu_keyboard(is_linked=False))
        return {"status": "handled", "command": "/disconnect"}

    # Command: /organization
    elif text.startswith("/organization"):
        if is_linked and identity.active_organization:
            response_text = (
                f"🏢 *Organisation Active Alliance One*\n\n"
                f"• *Nom* : *{identity.active_organization.name}*\n"
                f"• *Modules actifs* : {', '.join(identity.active_organization.active_modules or [])}\n\n"
                f"_La gestion multi-organisations complète sera activée en Phase 3._"
            )
        elif is_linked:
            response_text = "ℹ️ Aucune organisation spécifique n'est actuellement assignée à votre profil."
        else:
            response_text = "⚠️ Veuillez d'abord lier votre compte Alliance One avec `/connect`."
        client.send_message(chat_id, response_text, reply_markup=get_main_menu_keyboard(is_linked=is_linked))
        return {"status": "handled", "command": "/organization"}

    elif text.startswith("/help"):
        client.send_message(chat_id, HELP_MESSAGE, reply_markup=get_help_keyboard())
        return {"status": "handled", "command": "/help"}

    elif text.startswith("/community"):
        client.send_message(chat_id, COMMUNITY_MESSAGE, reply_markup=get_community_keyboard())
        return {"status": "handled", "command": "/community"}

    elif text.startswith("/status"):
        client.send_message(chat_id, STATUS_MESSAGE, reply_markup=get_main_menu_keyboard(is_linked=is_linked))
        return {"status": "handled", "command": "/status"}

    # Default fallback for free text in Phase 2
    fallback_text = (
        "Bonjour ! Je suis le bot officiel *Alliance One*.\n\n"
        "Pour commencer ou consulter les options disponibles, utilisez le menu ci-dessous :"
    )
    client.send_message(chat_id, fallback_text, reply_markup=get_main_menu_keyboard(is_linked=is_linked))
    return {"status": "handled", "command": "default_fallback"}

def handle_callback_query(callback_query: Dict[str, Any], client: TelegramClient) -> Dict[str, Any]:
    """
    Routes inline keyboard callback queries with identity context.
    """
    query_id = callback_query.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    from_user = callback_query.get("from", {})
    user_id = from_user.get("id") or chat_id

    if query_id:
        client.answer_callback_query(query_id)

    if not chat_id or not message_id:
        return {"status": "ignored", "reason": "missing_callback_metadata"}

    identity = resolve_telegram_identity(user_id) if user_id else None
    is_linked = identity is not None

    logger.info(f"Received Telegram callback query from user {user_id} (linked={is_linked}): '{data}'")

    if data == "btn_main_menu":
        client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=WELCOME_MESSAGE,
            reply_markup=get_main_menu_keyboard(is_linked=is_linked)
        )
        return {"status": "handled", "action": "main_menu"}

    elif data == "btn_help":
        client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=HELP_MESSAGE,
            reply_markup=get_help_keyboard()
        )
        return {"status": "handled", "action": "help"}

    elif data == "btn_ai_info":
        client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=AI_INFO_MESSAGE,
            reply_markup=get_help_keyboard()
        )
        return {"status": "handled", "action": "ai_info"}

    elif data == "btn_connect_info":
        client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=CONNECT_INFO_MESSAGE,
            reply_markup=get_help_keyboard()
        )
        return {"status": "handled", "action": "connect_info"}

    elif data == "btn_me":
        if is_linked:
            org_name = identity.active_organization.name if identity.active_organization else "Alliance One"
            verified_str = identity.verified_at.strftime('%d/%m/%Y à %H:%M') if identity.verified_at else "Actif"
            text = (
                f"👤 *Profil Alliance One Connecté*\n\n"
                f"• *Email* : `{identity.user.email}`\n"
                f"• *Nom* : {identity.first_name or identity.user.email}\n"
                f"• *Organisation active* : *{org_name}*\n"
                f"• *ID Telegram* : `{user_id}`\n"
                f"• *Liaison établie le* : {verified_str}\n"
                f"• *Statut* : Authentifié ✅"
            )
        else:
            text = (
                f"⚠️ *Compte non connecté*\n\n"
                f"Votre compte Telegram n'est pas encore associé à Alliance One.\n"
                f"Utilisez `/connect` pour associer votre compte."
            )
        client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=get_main_menu_keyboard(is_linked=is_linked)
        )
        return {"status": "handled", "action": "me"}

    elif data == "btn_organization":
        if is_linked and identity.active_organization:
            text = (
                f"🏢 *Organisation Active Alliance One*\n\n"
                f"• *Nom* : *{identity.active_organization.name}*\n"
                f"• *Modules actifs* : {', '.join(identity.active_organization.active_modules or [])}\n\n"
                f"_La gestion multi-organisations complète sera activée en Phase 3._"
            )
        elif is_linked:
            text = "ℹ️ Aucune organisation spécifique n'est actuellement assignée à votre profil."
        else:
            text = "⚠️ Veuillez d'abord lier votre compte Alliance One avec `/connect`."
        client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=get_main_menu_keyboard(is_linked=is_linked)
        )
        return {"status": "handled", "action": "organization"}

    elif data == "btn_disconnect":
        if is_linked:
            unlink_telegram_account(user_id)
            text = (
                f"🚪 *Compte dissocié avec succès*\n\n"
                f"Votre compte Telegram a été déconnecté d'Alliance One.\n"
                f"Pour reconnecter votre compte, tapez `/connect`."
            )
        else:
            text = "ℹ️ Aucun compte n'est actuellement associé."
        client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=get_main_menu_keyboard(is_linked=False)
        )
        return {"status": "handled", "action": "disconnect"}

    return {"status": "ignored", "reason": f"unknown_action_{data}"}

