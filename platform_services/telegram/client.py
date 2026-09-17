import logging
from typing import Dict, Any, Optional, Union, List
import requests
from django.conf import settings
from .exceptions import TelegramAPIError, TelegramConfigurationError

logger = logging.getLogger(__name__)

_shared_session: Optional[requests.Session] = None

def get_shared_session() -> requests.Session:
    global _shared_session
    if _shared_session is None:
        _shared_session = requests.Session()
    return _shared_session

class TelegramClient:
    """
    Clean, lightweight HTTP client for the official Telegram Bot API.
    Uses standard requests with strict timeout, connection pooling, sanitized logging, and error handling.
    """

    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, token: Optional[str] = None, timeout: int = 10, session: Optional[requests.Session] = None):
        if token is None:
            self.token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        else:
            self.token = token
        self.timeout = timeout
        self.session = session or get_shared_session()

    def _get_url(self, method: str) -> str:
        if not self.token:
            raise TelegramConfigurationError("TELEGRAM_BOT_TOKEN is not configured in settings or environment.")
        return f"{self.BASE_URL}{self.token}/{method}"

    def _post(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a POST request to Telegram Bot API with error handling and sanitized logs.
        """
        url = self._get_url(method)
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            data = response.json()
        except requests.exceptions.Timeout as e:
            logger.error(f"Telegram API timeout calling method '{method}'")
            raise TelegramAPIError(f"Telegram API timed out calling {method}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram API connection failure on method '{method}': {e}")
            raise TelegramAPIError(f"Telegram API connection error: {str(e)}") from e
        except ValueError as e:
            logger.error(f"Telegram API returned invalid non-JSON response for '{method}'")
            raise TelegramAPIError("Telegram API returned non-JSON response") from e

        if not data.get("ok"):
            error_description = data.get("description", "Unknown Telegram API error")
            error_code = data.get("error_code", response.status_code)
            logger.warning(f"Telegram API returned error for method '{method}': [{error_code}] {error_description}")
            raise TelegramAPIError(
                message=error_description,
                status_code=response.status_code,
                error_code=error_code
            )

        return data.get("result", {})

    def get_me(self) -> Dict[str, Any]:
        """Returns basic information about the bot."""
        return self._post("getMe", {})

    def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True
    ) -> Dict[str, Any]:
        """
        Sends a text message with optional inline keyboard.
        """
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }
        try:
            return self._post("sendMessage", payload)
        except TelegramAPIError as e:
            if "can't parse entities" in str(e).lower() and parse_mode:
                logger.warning(f"Telegram markdown parse error, falling back to plain text for chat {chat_id}")
                payload.pop("parse_mode", None)
                return self._post("sendMessage", payload)
            raise

    def edit_message_text(
        self,
        chat_id: Union[int, str],
        message_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True
    ) -> Dict[str, Any]:
        """
        Edits an existing message's text and markup with automatic markdown parse error fallback.
        """
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            return self._post("editMessageText", payload)
        except TelegramAPIError as e:
            if "can't parse entities" in str(e).lower() and parse_mode:
                logger.warning(f"Telegram markdown parse error on edit, falling back to plain text for chat {chat_id}")
                payload.pop("parse_mode", None)
                return self._post("editMessageText", payload)
            raise

    def send_chat_action(self, chat_id: Union[int, str], action: str = "typing") -> Dict[str, Any]:
        """
        Sends a status action (e.g. typing).
        """
        payload = {
            "chat_id": chat_id,
            "action": action
        }
        return self._post("sendChatAction", payload)

    def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> Dict[str, Any]:
        """
        Acknowledges an inline keyboard callback query.
        """
        payload: Dict[str, Any] = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert
        }
        if text:
            payload["text"] = text

        return self._post("answerCallbackQuery", payload)

    def set_webhook(
        self,
        url: str,
        secret_token: Optional[str] = None,
        allowed_updates: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Configures the HTTPS webhook URL with optional secret token.
        """
        payload: Dict[str, Any] = {"url": url}
        if secret_token:
            payload["secret_token"] = secret_token
        if allowed_updates:
            payload["allowed_updates"] = allowed_updates
        else:
            payload["allowed_updates"] = ["message", "callback_query"]

        return self._post("setWebhook", payload)

    def delete_webhook(self) -> Dict[str, Any]:
        """Removes the active webhook configuration."""
        return self._post("deleteWebhook", {})

    def get_webhook_info(self) -> Dict[str, Any]:
        """Retrieves current webhook status and configuration."""
        return self._post("getWebhookInfo", {})
