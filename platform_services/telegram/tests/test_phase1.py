import pytest
from unittest.mock import MagicMock, patch
from rest_framework.test import APIClient
from django.conf import settings
from platform_services.telegram.models import TelegramUpdateLog
from platform_services.telegram.client import TelegramClient
from platform_services.telegram.exceptions import TelegramAPIError, TelegramConfigurationError
from platform_services.telegram.handlers import handle_update, WELCOME_MESSAGE, HELP_MESSAGE, COMMUNITY_MESSAGE

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def secret_token():
    return getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', 'alliance-one-telegram-secret-token-2026')

@pytest.mark.django_db
def test_webhook_valid_accepted(api_client, secret_token):
    """
    Test 1: A valid webhook request with correct secret token is accepted.
    """
    payload = {
        "update_id": 10001,
        "message": {
            "message_id": 1,
            "from": {"id": 998877, "first_name": "Benjamin"},
            "chat": {"id": 998877, "type": "private"},
            "text": "/start"
        }
    }

    with patch.object(TelegramClient, 'send_message') as mock_send:
        mock_send.return_value = {"ok": True, "result": {}}
        response = api_client.post(
            '/api/integrations/telegram/webhook/',
            payload,
            format='json',
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret_token
        )

    assert response.status_code == 200
    assert response.data["status"] == "ok"
    assert response.data["update_id"] == 10001
    assert TelegramUpdateLog.objects.filter(update_id=10001).exists()
    mock_send.assert_called_once()

@pytest.mark.django_db
def test_webhook_invalid_secret_rejected(api_client):
    """
    Test 2: A webhook request with invalid secret token is rejected with 403 Forbidden.
    """
    payload = {
        "update_id": 10002,
        "message": {
            "message_id": 2,
            "chat": {"id": 12345},
            "text": "/start"
        }
    }

    response = api_client.post(
        '/api/integrations/telegram/webhook/',
        payload,
        format='json',
        HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="wrong-malicious-secret"
    )

    assert response.status_code == 403
    assert not TelegramUpdateLog.objects.filter(update_id=10002).exists()

@pytest.mark.django_db
def test_webhook_idempotency_duplicate_update(api_client, secret_token):
    """
    Test 3: An update_id that was already processed is detected as duplicate
    and not re-executed (single-execution semantics).
    """
    payload = {
        "update_id": 10003,
        "message": {
            "message_id": 3,
            "chat": {"id": 55555},
            "text": "/help"
        }
    }

    with patch.object(TelegramClient, 'send_message') as mock_send:
        mock_send.return_value = {"ok": True, "result": {}}
        
        # 1st call: processed
        res1 = api_client.post(
            '/api/integrations/telegram/webhook/',
            payload,
            format='json',
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret_token
        )
        assert res1.status_code == 200
        assert res1.data["status"] == "ok"
        assert mock_send.call_count == 1

        # 2nd call with identical update_id: must skip execution
        res2 = api_client.post(
            '/api/integrations/telegram/webhook/',
            payload,
            format='json',
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret_token
        )
        assert res2.status_code == 200
        assert res2.data["status"] == "already_processed"
        # Handler must NOT have been called a second time
        assert mock_send.call_count == 1

@pytest.mark.django_db
def test_start_command_response():
    """
    Test 4: /start command sends welcome message and interactive menu.
    """
    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 10004,
        "message": {
            "message_id": 4,
            "chat": {"id": 11111},
            "text": "/start"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["command"] == "/start"
    mock_client.send_message.assert_called_once()
    args, kwargs = mock_client.send_message.call_args
    assert args[0] == 11111
    assert "Bienvenue sur Alliance One" in args[1]
    assert "inline_keyboard" in kwargs.get("reply_markup", {})

@pytest.mark.django_db
def test_help_command_response():
    """
    Test 5: /help command returns complete help text and commands list.
    """
    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 10005,
        "message": {
            "message_id": 5,
            "chat": {"id": 22222},
            "text": "/help"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["command"] == "/help"
    mock_client.send_message.assert_called_once()
    args, kwargs = mock_client.send_message.call_args
    assert args[0] == 22222
    assert "Centre d'Aide" in args[1]

@pytest.mark.django_db
def test_community_command_response():
    """
    Test 6: /community command returns official links for community & channel.
    """
    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 10006,
        "message": {
            "message_id": 6,
            "chat": {"id": 33333},
            "text": "/community"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["command"] == "/community"
    mock_client.send_message.assert_called_once()
    args, kwargs = mock_client.send_message.call_args
    assert args[0] == 33333
    assert "Communauté Alliance One" in args[1]

@pytest.mark.django_db
def test_invalid_payload_fail_closed(api_client, secret_token):
    """
    Test 7: Malformed or missing update_id payload is rejected (Fail Closed).
    """
    # Missing update_id
    response = api_client.post(
        '/api/integrations/telegram/webhook/',
        {"message": {"text": "hello"}},
        format='json',
        HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret_token
    )
    assert response.status_code == 400
    assert "missing 'update_id'" in response.data["error"]

    # Non-dict payload
    response2 = api_client.post(
        '/api/integrations/telegram/webhook/',
        "just a string",
        format='json',
        HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret_token
    )
    assert response2.status_code == 400

@pytest.mark.django_db
def test_telegram_api_error_handling():
    """
    Test 8: Telegram Bot API network / response error is safely wrapped in TelegramAPIError.
    """
    client = TelegramClient(token="mock-token-12345")
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "ok": False,
        "error_code": 400,
        "description": "Bad Request: chat not found"
    }

    with patch.object(client.session, 'post', return_value=mock_response):
        with pytest.raises(TelegramAPIError) as exc_info:
            client.send_message(chat_id=99999999, text="Test message")

        assert "chat not found" in str(exc_info.value)
        assert exc_info.value.status_code == 400

def test_missing_token_configuration():
    """
    Test 9: TelegramClient raises TelegramConfigurationError when token is not configured.
    """
    client = TelegramClient(token="")
    with pytest.raises(TelegramConfigurationError) as exc_info:
        client.get_me()

    assert "TELEGRAM_BOT_TOKEN is not configured" in str(exc_info.value)

@pytest.mark.django_db
def test_health_endpoint(api_client):
    """
    Test 10: Health check endpoint returns operational status and configuration.
    """
    response = api_client.get('/api/integrations/telegram/health/')
    assert response.status_code == 200
    assert response.data["status"] == "healthy"
    assert response.data["service"] == "alliance_one_telegram"
    assert "configured" in response.data

@pytest.mark.django_db
def test_callback_query_routing():
    """
    Test 11: Callback query for inline buttons updates message and answers query.
    """
    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 10011,
        "callback_query": {
            "id": "query_777",
            "from": {"id": 44444},
            "message": {
                "message_id": 77,
                "chat": {"id": 44444}
            },
            "data": "btn_help"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["action"] == "help"
    mock_client.answer_callback_query.assert_called_once_with("query_777")
    mock_client.edit_message_text.assert_called_once()
    assert "Centre d'Aide" in mock_client.edit_message_text.call_args[1]["text"]
