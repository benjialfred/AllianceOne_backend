from typing import Dict, Any, List
from django.conf import settings

def get_main_menu_keyboard() -> Dict[str, Any]:
    """
    Returns the primary interactive inline keyboard for Alliance One.
    """
    community_url = getattr(settings, 'TELEGRAM_COMMUNITY_URL', 'https://t.me/allianceonecommunity')
    channel_url = getattr(settings, 'TELEGRAM_CHANNEL_URL', 'https://t.me/allianceonechannels')

    keyboard: List[List[Dict[str, str]]] = [
        [
            {"text": "🤖 Alliance AI", "callback_data": "btn_ai_info"}
        ],
        [
            {"text": "👥 Communauté", "url": community_url},
            {"text": "📢 Canal Officiel", "url": channel_url}
        ],
        [
            {"text": "❓ Aide & Commandes", "callback_data": "btn_help"}
        ]
    ]
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
