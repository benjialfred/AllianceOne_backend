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

*Commandes disponibles (Phase 1) :*
• `/start` — Affiche le message de bienvenue et le menu interactif.
• `/help` — Affiche ce message d'aide.
• `/community` — Liens vers notre groupe et canal officiel.
• `/status` — Vérifie l'état opérationnel du bot.

*Fonctionnalités à venir :*
• `/connect` — Lier votre compte utilisateur Alliance One de manière sécurisée (Phase 2).
• `/organization` — Gérer et basculer votre organisation active (Phase 3).
• `/ai` — Poser des questions et exécuter des missions avec Alliance AI (Phase 4 & 5).

Pour toute question technique, rejoignez notre groupe d'entraide !
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
• *Version de l'intégration* : V1.0 (Phase 1 Foundation)
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
    Routes incoming text messages and commands.
    """
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()

    if not chat_id:
        return {"status": "ignored", "reason": "missing_chat_id"}

    logger.info(f"Received Telegram message from chat {chat_id}: '{text}'")

    if text.startswith("/start"):
        client.send_message(chat_id, WELCOME_MESSAGE, reply_markup=get_main_menu_keyboard())
        return {"status": "handled", "command": "/start"}

    elif text.startswith("/help"):
        client.send_message(chat_id, HELP_MESSAGE, reply_markup=get_help_keyboard())
        return {"status": "handled", "command": "/help"}

    elif text.startswith("/community"):
        client.send_message(chat_id, COMMUNITY_MESSAGE, reply_markup=get_community_keyboard())
        return {"status": "handled", "command": "/community"}

    elif text.startswith("/status"):
        client.send_message(chat_id, STATUS_MESSAGE, reply_markup=get_main_menu_keyboard())
        return {"status": "handled", "command": "/status"}

    # Default fallback for free text in Phase 1
    fallback_text = (
        "Bonjour ! Je suis le bot officiel *Alliance One*.\n\n"
        "Pour commencer ou consulter les options disponibles, utilisez le menu ci-dessous :"
    )
    client.send_message(chat_id, fallback_text, reply_markup=get_main_menu_keyboard())
    return {"status": "handled", "command": "default_fallback"}

def handle_callback_query(callback_query: Dict[str, Any], client: TelegramClient) -> Dict[str, Any]:
    """
    Routes inline keyboard callback queries.
    """
    query_id = callback_query.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    if query_id:
        client.answer_callback_query(query_id)

    if not chat_id or not message_id:
        return {"status": "ignored", "reason": "missing_callback_metadata"}

    logger.info(f"Received Telegram callback query from chat {chat_id}: '{data}'")

    if data == "btn_main_menu":
        client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=WELCOME_MESSAGE,
            reply_markup=get_main_menu_keyboard()
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

    return {"status": "ignored", "reason": f"unknown_action_{data}"}
