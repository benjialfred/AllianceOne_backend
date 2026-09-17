import pytest
from unittest.mock import MagicMock
from rest_framework.test import APIClient
from platform_services.identity.models import User, Organization, Role, Membership
from platform_services.telegram.models import TelegramIdentity
from platform_services.telegram.identity import (
    get_user_memberships,
    get_active_membership,
    switch_active_organization,
    resolve_telegram_identity,
)
from platform_services.telegram.handlers import handle_update
from platform_services.telegram.client import TelegramClient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def org_alpha(db):
    return Organization.objects.create(name="Alliance Académie Alpha", active_modules=["education_core", "finance"])

@pytest.fixture
def org_beta(db):
    return Organization.objects.create(name="Clinique Santé Espoir", active_modules=["health_core", "inventory"])

@pytest.fixture
def org_unauthorized(db):
    return Organization.objects.create(name="Organisation Confidentielle", active_modules=["defense"])

@pytest.fixture
def role_alpha(db, org_alpha):
    return Role.objects.create(name="Directeur Général", organization=org_alpha)

@pytest.fixture
def role_beta(db, org_beta):
    return Role.objects.create(name="Administrateur", organization=org_beta)

@pytest.fixture
def multi_tenant_user(db, org_alpha, org_beta, role_alpha, role_beta):
    user = User.objects.create(email="executive@allianceone.org")
    Membership.objects.create(user=user, organization=org_alpha, role=role_alpha)
    Membership.objects.create(user=user, organization=org_beta, role=role_beta)
    return user

@pytest.fixture
def linked_identity(db, multi_tenant_user, org_alpha):
    return TelegramIdentity.objects.create(
        user=multi_tenant_user,
        telegram_user_id=12349999,
        telegram_chat_id=12349999,
        username="exec_tg",
        first_name="Executive",
        active_organization=org_alpha,
        is_active=True
    )

@pytest.mark.django_db
def test_single_organization_view(db, org_alpha, role_alpha):
    """
    Test 1: When a user belongs to a single organization, /organization shows
    complete details and notes that it is their sole organization.
    """
    single_user = User.objects.create(email="single@allianceone.org")
    Membership.objects.create(user=single_user, organization=org_alpha, role=role_alpha)
    TelegramIdentity.objects.create(
        user=single_user,
        telegram_user_id=555111,
        telegram_chat_id=555111,
        active_organization=org_alpha,
        is_active=True
    )

    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 30001,
        "message": {
            "message_id": 201,
            "from": {"id": 555111},
            "chat": {"id": 555111},
            "text": "/organization"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["command"] == "/organization"
    assert result["count"] == 1

    mock_client.send_message.assert_called_once()
    msg_text = mock_client.send_message.call_args[0][1]
    assert "Alliance Académie Alpha" in msg_text
    assert "Directeur Général" in msg_text
    assert "Organisation unique" in msg_text

@pytest.mark.django_db
def test_multi_organization_view_and_keyboard(linked_identity, org_alpha, org_beta):
    """
    Test 2: When a user belongs to multiple organizations, /organization displays
    the count and renders an interactive switch keyboard with all choices.
    """
    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 30002,
        "message": {
            "message_id": 202,
            "from": {"id": 12349999},
            "chat": {"id": 12349999},
            "text": "/organization"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["command"] == "/organization"
    assert result["count"] == 2

    mock_client.send_message.assert_called_once()
    args, kwargs = mock_client.send_message.call_args
    assert "Vos Organisations Alliance One" in args[1]
    assert "(2)" in args[1]
    assert "Alliance Académie Alpha" in args[1]

    # Verify inline keyboard has buttons for both organizations
    reply_markup = kwargs.get("reply_markup", {})
    inline_keyboard = reply_markup.get("inline_keyboard", [])
    button_texts = [btn["text"] for row in inline_keyboard for btn in row if "text" in btn]
    assert any("Alliance Académie Alpha" in t and "Actif ✅" in t for t in button_texts)
    assert any("Clinique Santé Espoir" in t for t in button_texts)

@pytest.mark.django_db
def test_switch_organization_authorized_success(linked_identity, org_alpha, org_beta):
    """
    Test 3: User clicks on an authorized organization -> switches active organization.
    """
    assert linked_identity.active_organization == org_alpha

    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 30003,
        "callback_query": {
            "id": "query_switch_1",
            "from": {"id": 12349999},
            "message": {"message_id": 203, "chat": {"id": 12349999}},
            "data": f"btn_switch_org:{org_beta.id}"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["action"] == "switch_org"
    assert result["success"] is True
    assert result["org_id"] == str(org_beta.id)

    # Verify identity updated in DB
    linked_identity.refresh_from_db()
    assert linked_identity.active_organization == org_beta

    mock_client.answer_callback_query.assert_called_once_with(
        "query_switch_1",
        text="Bascule vers Clinique Santé Espoir réussie !"
    )
    mock_client.edit_message_text.assert_called_once()
    assert "Clinique Santé Espoir" in mock_client.edit_message_text.call_args[1]["text"]

@pytest.mark.django_db
def test_switch_organization_unauthorized_fail_closed(linked_identity, org_alpha, org_unauthorized):
    """
    Test 4: Fail-Closed Security: User attempts to switch to an organization
    they are NOT a member of -> rejected immediately, identity unchanged.
    """
    assert linked_identity.active_organization == org_alpha

    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 30004,
        "callback_query": {
            "id": "query_switch_hack",
            "from": {"id": 12349999},
            "message": {"message_id": 204, "chat": {"id": 12349999}},
            "data": f"btn_switch_org:{org_unauthorized.id}"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["action"] == "switch_org"
    assert result["success"] is False
    assert "Accès refusé" in result["error"]

    # Verify identity in DB was NOT changed
    linked_identity.refresh_from_db()
    assert linked_identity.active_organization == org_alpha

    # Alert shown to user
    mock_client.answer_callback_query.assert_called_once_with(
        "query_switch_hack",
        text="Accès refusé : organisation non autorisée !",
        show_alert=True
    )

@pytest.mark.django_db
def test_noop_current_org_click(linked_identity, org_alpha):
    """
    Test 5: Clicking on already-active organization triggers noop notice.
    """
    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 30005,
        "callback_query": {
            "id": "query_noop",
            "from": {"id": 12349999},
            "message": {"message_id": 205, "chat": {"id": 12349999}},
            "data": "noop_current_org"
        }
    }

    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["action"] == "noop_current_org"
    mock_client.answer_callback_query.assert_called_once_with(
        "query_noop",
        text="Cette organisation est déjà votre organisation active."
    )

@pytest.mark.django_db
def test_revoked_membership_auto_heal(linked_identity, multi_tenant_user, org_alpha, org_beta):
    """
    Test 6: If the user's active membership is revoked/deleted, get_active_membership
    automatically heals by falling back to another valid membership.
    """
    assert linked_identity.active_organization == org_alpha

    # Revoke membership in Org Alpha
    Membership.objects.filter(user=multi_tenant_user, organization=org_alpha).delete()

    # Call get_active_membership
    healed_membership = get_active_membership(linked_identity)
    assert healed_membership is not None
    assert healed_membership.organization == org_beta

    # Verify identity in DB was updated to Org Beta
    linked_identity.refresh_from_db()
    assert linked_identity.active_organization == org_beta

@pytest.mark.django_db
def test_all_memberships_revoked(linked_identity, multi_tenant_user):
    """
    Test 7: If all memberships are revoked, get_active_membership returns None
    and /organization notifies the user.
    """
    Membership.objects.filter(user=multi_tenant_user).delete()

    active_membership = get_active_membership(linked_identity)
    assert active_membership is None

    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 30007,
        "message": {
            "message_id": 207,
            "from": {"id": 12349999},
            "chat": {"id": 12349999},
            "text": "/organization"
        }
    }
    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["count"] == 0
    assert "Aucune organisation active" in mock_client.send_message.call_args[0][1]

@pytest.mark.django_db
def test_unlinked_user_organization_rejected():
    """
    Test 8: Unlinked Telegram user cannot inspect or manipulate organizations.
    """
    mock_client = MagicMock(spec=TelegramClient)
    update = {
        "update_id": 30008,
        "message": {
            "message_id": 208,
            "from": {"id": 99999999},
            "chat": {"id": 99999999},
            "text": "/organization"
        }
    }
    result = handle_update(update, mock_client)
    assert result["status"] == "handled"
    assert result["is_linked"] is False
    assert "/connect" in mock_client.send_message.call_args[0][1]

@pytest.mark.django_db
def test_web_switch_org_api_success_and_forbidden(api_client, multi_tenant_user, linked_identity, org_alpha, org_beta, org_unauthorized):
    """
    Test 9: /api/integrations/telegram/switch-org/ REST API allows valid switch
    and rejects unauthorized switch with 403 Forbidden.
    """
    api_client.force_authenticate(user=multi_tenant_user)

    # 1. Valid switch to Org Beta -> 200
    res_valid = api_client.post('/api/integrations/telegram/switch-org/', {"organization_id": str(org_beta.id)})
    assert res_valid.status_code == 200
    assert res_valid.data["status"] == "success"
    assert res_valid.data["active_organization"]["name"] == "Clinique Santé Espoir"

    linked_identity.refresh_from_db()
    assert linked_identity.active_organization == org_beta

    # 2. Unauthorized switch to Org Unauthorized -> 403 Forbidden
    res_invalid = api_client.post('/api/integrations/telegram/switch-org/', {"organization_id": str(org_unauthorized.id)})
    assert res_invalid.status_code == 403
    assert "Accès refusé" in res_invalid.data["error"]

    # Identity remains in Org Beta
    linked_identity.refresh_from_db()
    assert linked_identity.active_organization == org_beta
