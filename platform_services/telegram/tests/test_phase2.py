import pytest
from datetime import timedelta
from unittest.mock import MagicMock, patch
from django.utils import timezone
from rest_framework.test import APIClient
from platform_services.identity.models import User, Organization, Role, Membership
from platform_services.telegram.models import TelegramIdentity, TelegramLinkCode
from platform_services.telegram.identity import generate_link_code, get_deep_link, link_telegram_account, resolve_telegram_identity, unlink_telegram_account
from platform_services.telegram.handlers import handle_update
from platform_services.telegram.client import TelegramClient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def secret_token():
    return "alliance-one-telegram-secret-token-2026"

@pytest.fixture
def test_organization(db):
    return Organization.objects.create(name="Alliance Académie", active_modules=["education_core", "finance"])

@pytest.fixture
def test_role(db, test_organization):
    return Role.objects.create(name="Director", organization=test_organization)

@pytest.fixture
def test_user(db, test_organization, test_role):
    user = User.objects.create(email="director@allianceone.org")
    Membership.objects.create(user=user, organization=test_organization, role=test_role)
    return user

@pytest.mark.django_db
def test_generate_link_code_and_deep_link(test_user):
    """
    Test 1: generate_link_code creates an ALX- prefixed code expiring in 10 minutes,
    and get_deep_link builds the official https://t.me/ deep link.
    """
    link_code = generate_link_code(test_user, ttl_minutes=10)
    assert link_code.code.startswith("ALX-")
    assert link_code.user == test_user
    assert link_code.used_at is None
    assert link_code.is_valid is True

    deep_link = get_deep_link(link_code.code)
    assert f"https://t.me/AllianceOneAIBot?start={link_code.code}" == deep_link

@pytest.mark.django_db
def test_web_link_code_endpoint(api_client, test_user):
    """
    Test 2: Authenticated web user requests link code via REST API.
    Unauthenticated request is rejected (401/403).
    """
    # Unauthenticated -> rejected
    unauth_res = api_client.post('/api/integrations/telegram/link-code/')
    assert unauth_res.status_code in [401, 403]

    # Authenticated -> success
    api_client.force_authenticate(user=test_user)
    res = api_client.post('/api/integrations/telegram/link-code/')
    assert res.status_code == 200
    assert res.data["status"] == "success"
    assert res.data["code"].startswith("ALX-")
    assert "t.me/AllianceOneAIBot?start=" in res.data["deep_link"]
    assert res.data["valid_minutes"] == 10

@pytest.mark.django_db
def test_deep_link_account_linking_success(test_user, test_organization):
    """
    Test 3: User clicks deep link in Telegram -> receives /start ALX-CODE.
    Account is linked, identity created, primary organization set.
    """
    link_code = generate_link_code(test_user)
    mock_client = MagicMock(spec=TelegramClient)

    update = {
        "update_id": 20001,
        "message": {
            "message_id": 101,
            "from": {"id": 88776655, "username": "alice_tg", "first_name": "Alice"},
            "chat": {"id": 88776655},
            "text": f"/start {link_code.code}"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["command"] == "/start_deep_link"
    assert result["success"] is True

    # Check database state
    identity = resolve_telegram_identity(88776655)
    assert identity is not None
    assert identity.user == test_user
    assert identity.active_organization == test_organization
    assert identity.username == "alice_tg"
    assert identity.is_active is True
    assert identity.verified_at is not None

    # Code must now be marked used
    link_code.refresh_from_db()
    assert link_code.used_at is not None
    assert link_code.is_valid is False

    # Check confirmation message sent to user
    mock_client.send_message.assert_called_once()
    args, kwargs = mock_client.send_message.call_args
    assert "Félicitations" in args[1]
    assert "Alliance Académie" in args[1]
    assert test_user.email in args[1]

@pytest.mark.django_db
def test_replay_used_link_code_rejected(test_user):
    """
    Test 4: Single-use guarantee - using an already used link code fails.
    """
    link_code = generate_link_code(test_user)
    mock_client = MagicMock(spec=TelegramClient)

    # 1st use: success
    success1, _, _ = link_telegram_account(991122, 991122, link_code.code)
    assert success1 is True

    # 2nd use: rejected
    success2, msg2, _ = link_telegram_account(991133, 991133, link_code.code)
    assert success2 is False
    assert "déjà été utilisé" in msg2

@pytest.mark.django_db
def test_expired_link_code_rejected(test_user):
    """
    Test 5: An expired code (>10 minutes old) is rejected.
    """
    link_code = generate_link_code(test_user)
    link_code.expires_at = timezone.now() - timedelta(minutes=5)
    link_code.save()

    success, msg, _ = link_telegram_account(992233, 992233, link_code.code)
    assert success is False
    assert "expiré" in msg

@pytest.mark.django_db
def test_invalid_link_code_rejected():
    """
    Test 6: Non-existent code is rejected (Fail-Closed).
    """
    success, msg, _ = link_telegram_account(993344, 993344, "ALX-UNKNOWN99")
    assert success is False
    assert "invalide ou inexistant" in msg

@pytest.mark.django_db
def test_manual_connect_code_command(test_user, test_organization):
    """
    Test 7: User manually types '/connect ALX-CODE' in Telegram.
    """
    link_code = generate_link_code(test_user)
    mock_client = MagicMock(spec=TelegramClient)

    update = {
        "update_id": 20002,
        "message": {
            "message_id": 102,
            "from": {"id": 77665544, "username": "bob_tg"},
            "chat": {"id": 77665544},
            "text": f"/connect {link_code.code}"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["command"] == "/connect"
    assert result["success"] is True

    identity = resolve_telegram_identity(77665544)
    assert identity is not None
    assert identity.user == test_user

@pytest.mark.django_db
def test_me_command_linked_and_unlinked(test_user, test_organization):
    """
    Test 8: /me shows linked profile when connected, or prompt to connect when unlinked.
    """
    mock_client = MagicMock(spec=TelegramClient)

    # 1. Unlinked check
    update_unlinked = {
        "update_id": 20003,
        "message": {
            "message_id": 103,
            "from": {"id": 123456},
            "chat": {"id": 123456},
            "text": "/me"
        }
    }
    res_unlinked = handle_update(update_unlinked, mock_client)
    assert res_unlinked["status"] == "handled"
    assert res_unlinked["is_linked"] is False
    assert "non connecté" in mock_client.send_message.call_args[0][1]

    # 2. Link account
    link_code = generate_link_code(test_user)
    link_telegram_account(123456, 123456, link_code.code)

    # 3. Linked check
    mock_client.reset_mock()
    update_linked = {
        "update_id": 20004,
        "message": {
            "message_id": 104,
            "from": {"id": 123456},
            "chat": {"id": 123456},
            "text": "/me"
        }
    }
    res_linked = handle_update(update_linked, mock_client)
    assert res_linked["status"] == "handled"
    assert res_linked["is_linked"] is True
    assert test_user.email in mock_client.send_message.call_args[0][1]
    assert "Alliance Académie" in mock_client.send_message.call_args[0][1]

@pytest.mark.django_db
def test_disconnect_command(test_user):
    """
    Test 9: /disconnect deactivates Telegram identity.
    """
    link_code = generate_link_code(test_user)
    link_telegram_account(654321, 654321, link_code.code)
    assert resolve_telegram_identity(654321) is not None

    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 20005,
        "message": {
            "message_id": 105,
            "from": {"id": 654321},
            "chat": {"id": 654321},
            "text": "/disconnect"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["command"] == "/disconnect"

    # Identity must now be inactive
    assert resolve_telegram_identity(654321) is None
    mock_client.send_message.assert_called_once()
    assert "dissocié" in mock_client.send_message.call_args[0][1]

@pytest.mark.django_db
def test_web_status_and_unlink_endpoints(api_client, test_user, test_organization):
    """
    Test 10: /api/integrations/telegram/status/ and /unlink/ REST endpoints.
    """
    api_client.force_authenticate(user=test_user)

    # Initial status: not linked
    res1 = api_client.get('/api/integrations/telegram/status/')
    assert res1.status_code == 200
    assert res1.data["is_linked"] is False

    # Link via code
    link_code = generate_link_code(test_user)
    link_telegram_account(778899, 778899, link_code.code, username="tg_user")

    # Status: linked
    res2 = api_client.get('/api/integrations/telegram/status/')
    assert res2.status_code == 200
    assert res2.data["is_linked"] is True
    assert res2.data["telegram_username"] == "tg_user"
    assert res2.data["active_organization"]["name"] == "Alliance Académie"

    # Unlink via web endpoint
    res3 = api_client.post('/api/integrations/telegram/unlink/')
    assert res3.status_code == 200
    assert res3.data["status"] == "success"

    # Status after unlink: not linked
    res4 = api_client.get('/api/integrations/telegram/status/')
    assert res4.status_code == 200
    assert res4.data["is_linked"] is False
