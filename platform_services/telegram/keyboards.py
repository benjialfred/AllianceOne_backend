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
        app_settings_url = getattr(settings, 'ALLIANCE_WEB_SETTINGS_URL', 'https://allianceone-frontend.vercel.app/app/settings?telegram=connect')
        keyboard.append([
            {"text": "🌐 Ouvrir Alliance One (Lier mon compte)", "url": app_settings_url}
        ])
        keyboard.append([
            {"text": "ℹ️ Instructions de liaison (/connect)", "callback_data": "btn_connect_info"}
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

def get_connect_keyboard() -> Dict[str, Any]:
    """
    Returns the inline keyboard for connection and linking instructions,
    featuring a direct 1-click web button opening the platform settings/linking modal.
    """
    app_settings_url = getattr(settings, 'ALLIANCE_WEB_SETTINGS_URL', 'https://allianceone-frontend.vercel.app/app/settings?telegram=connect')
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🌐 Ouvrir Alliance One Web (Générer mon code)",
                    "url": app_settings_url
                }
            ],
            [
                {"text": "🔙 Menu Principal", "callback_data": "btn_main_menu"},
                {"text": "❓ Aide", "callback_data": "btn_help"}
            ]
        ]
    }

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

def get_ai_confirmation_keyboard(plan_id: str, step_id: str, action_hash: str) -> Dict[str, Any]:
    """
    Constructs an inline confirmation keyboard for sensitive AI tool executions.
    Enforces canonical action hash binding.
    """
    return {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Confirmer l'action",
                    "callback_data": f"ai_confirm:{plan_id}:{step_id}:{action_hash}"
                },
                {
                    "text": "❌ Annuler",
                    "callback_data": f"ai_cancel:{plan_id}:{step_id}"
                }
            ],
            [
                {"text": "🔙 Menu Principal", "callback_data": "btn_main_menu"}
            ]
        ]
    }

def get_ai_quick_keyboard() -> Dict[str, Any]:
    """
    Quick response keyboard after conversational AI answers.
    """
    return {
        "inline_keyboard": [
            [
                {"text": "🏢 Organisation", "callback_data": "btn_organization"},
                {"text": "🔙 Menu Principal", "callback_data": "btn_main_menu"}
            ]
        ]
    }


