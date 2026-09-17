from typing import Dict, Any, List
from django.conf import settings

def get_main_menu_keyboard(is_linked: bool = False) -> Dict[str, Any]:
    """
    Returns the primary interactive inline keyboard for Alliance One.
    Adapts options based on whether the user's Telegram identity is verified.
    """
    community_url = getattr(settings, 'TELEGRAM_COMMUNITY_URL', 'https://t.me/allianceonecommunity')
    channel_url = getattr(settings, 'TELEGRAM_CHANNEL_URL', 'https://t.me/allianceonechannels')

    keyboard: List[List[Dict[str, str]]] = [
        [
            {"text": "🤖 Alliance AI", "callback_data": "btn_ai_info"}
        ]
    ]

    if is_linked:
        keyboard.append([
            {"text": "👤 Mon Compte (/me)", "callback_data": "btn_me"},
            {"text": "🏢 Organisation", "callback_data": "btn_organization"}
        ])
    else:
        keyboard.append([
            {"text": "🔗 Lier mon compte Alliance One", "callback_data": "btn_connect_info"}
        ])

    keyboard.append([
        {"text": "👥 Communauté", "url": community_url},
        {"text": "📢 Canal Officiel", "url": channel_url}
    ])

    bottom_row = [{"text": "❓ Aide & Commandes", "callback_data": "btn_help"}]
    if is_linked:
        bottom_row.append({"text": "🚪 Déconnexion", "callback_data": "btn_disconnect"})
    keyboard.append(bottom_row)

    return {"inline_keyboard": keyboard}

def get_help_keyboard() -> Dict[str, Any]:
    """
    Returns the inline keyboard for the /help section.
    """
    community_url = getattr(settings, 'TELEGRAM_COMMUNITY_URL', 'https://t.me/allianceonecommunity')

    keyboard: List[List[Dict[str, str]]] = [
        [
            {"text": "👥 Rejoindre la Communauté", "url": community_url}
        ],
        [
            {"text": "🔙 Menu Principal", "callback_data": "btn_main_menu"}
        ]
    ]
    return {"inline_keyboard": keyboard}

def get_community_keyboard() -> Dict[str, Any]:
    """
    Returns the inline keyboard for the /community section.
    """
    community_url = getattr(settings, 'TELEGRAM_COMMUNITY_URL', 'https://t.me/allianceonecommunity')
    channel_url = getattr(settings, 'TELEGRAM_CHANNEL_URL', 'https://t.me/allianceonechannels')

    keyboard: List[List[Dict[str, str]]] = [
        [
            {"text": "👥 Rejoindre le Groupe Communautaire", "url": community_url}
        ],
        [
            {"text": "📢 Suivre le Canal Officiel", "url": channel_url}
        ],
        [
            {"text": "🔙 Menu Principal", "callback_data": "btn_main_menu"}
        ]
    ]
    return {"inline_keyboard": keyboard}

def get_organization_switch_keyboard(user_memberships, current_active_org_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Constructs an interactive inline keyboard allowing multi-organization users
    to seamlessly switch their active tenant context.
    """
    keyboard: List[List[Dict[str, str]]] = []

    for m in user_memberships:
        is_current = str(m.organization_id) == str(current_active_org_id)
        status_label = " (Actif ✅)" if is_current else ""
        btn_text = f"🏢 {m.organization.name}{status_label}"
        callback_data = "noop_current_org" if is_current else f"btn_switch_org:{m.organization_id}"
        keyboard.append([{"text": btn_text, "callback_data": callback_data}])

    keyboard.append([
        {"text": "🔙 Menu Principal", "callback_data": "btn_main_menu"}
    ])
    return {"inline_keyboard": keyboard}

