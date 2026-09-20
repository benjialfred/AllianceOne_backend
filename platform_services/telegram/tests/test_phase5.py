import pytest
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from platform_services.identity.models import Organization, Role, Membership
from platform_services.telegram.models import (
    TelegramIdentity,
    TelegramNotificationLog,
    TelegramNotificationPreference
)
from platform_services.telegram.client import TelegramClient
from platform_services.telegram.notification_service import TelegramNotificationService
from platform_services.telegram.handlers import handle_update, handle_message, handle_callback_query
from rest_framework.test import APIRequestFactory, force_authenticate
from platform_services.telegram.web_views import TelegramPreferencesView, TelegramTestNotificationView

User = get_user_model()

@pytest.fixture
def mock_telegram_client():
    client = MagicMock(spec=TelegramClient)
    client.send_message.return_value = {"message_id": 999111, "ok": True}
    client.edit_message_text.return_value = {"message_id": 999111, "ok": True}
    client.send_chat_action.return_value = {"ok": True}
    client.answer_callback_query.return_value = {"ok": True}
    return client

@pytest.fixture
def notification_setup(db):
    user_admin = User.objects.create(email="admin_notif@example.com")
    user_staff = User.objects.create(email="staff_notif@example.com")
    user_unlinked = User.objects.create(email="unlinked@example.com")

    org = Organization.objects.create(
        name="Alliance High School",
        active_modules=["education", "finance", "inventory"]
    )
    role_admin = Role.objects.create(name="ADMINISTRATOR", organization=org)
    role_staff = Role.objects.create(name="TEACHER", organization=org)

    m1 = Membership.objects.create(user=user_admin, organization=org, role=role_admin)
    m2 = Membership.objects.create(user=user_staff, organization=org, role=role_staff)

    id_admin = TelegramIdentity.objects.create(
        telegram_user_id=111222,
        telegram_chat_id=111222,
        user=user_admin,
        active_organization=org,
        is_active=True
    )
    id_staff = TelegramIdentity.objects.create(
        telegram_user_id=333444,
        telegram_chat_id=333444,
        user=user_staff,
        active_organization=org,
        is_active=True
    )

    return {
        "admin": user_admin,
        "staff": user_staff,
        "unlinked": user_unlinked,
        "org": org,
        "role_admin": role_admin,
        "role_staff": role_staff,
        "id_admin": id_admin,
        "id_staff": id_staff
    }

@pytest.mark.django_db
def test_send_user_notification_success(mock_telegram_client, notification_setup):
    """
    Verified user receives alert, and TelegramNotificationLog transitions to DELIVERED.
    """
    service = TelegramNotificationService(client=mock_telegram_client)
    res = service.send_user_notification(
        user=notification_setup["admin"],
        title="Facture Impayée #INV-001",
        message="Le client Société ABC a une facture en retard de 500 000 FCFA.",
        level=TelegramNotificationLog.LEVEL_WARNING,
        category="finance",
        actions=[{"text": "Voir Facture", "url": "https://app.allianceone.com/finance/inv-001"}],
        idempotency_key="inv_001_alert"
    )

    assert res["status"] == "delivered"
    assert res["telegram_message_id"] == 999111
    mock_telegram_client.send_message.assert_called_once()
    args, kwargs = mock_telegram_client.send_message.call_args
    chat_id = kwargs.get("chat_id") or (args[0] if args else None)
    assert chat_id == 111222
    assert "Facture Impayée #INV-001" in kwargs["text"]
    assert "FINANCES & FACTURATION" in kwargs["text"]
    assert kwargs["reply_markup"]["inline_keyboard"][0][0]["text"] == "Voir Facture"

    # Verify DB Log
    log = TelegramNotificationLog.objects.get(idempotency_key="inv_001_alert")
    assert log.status == TelegramNotificationLog.STATUS_DELIVERED
    assert log.telegram_message_id == 999111
    assert log.sent_at is not None

@pytest.mark.django_db
def test_send_user_notification_unlinked(mock_telegram_client, notification_setup):
    """
    Sending notification to unlinked user is skipped gracefully.
    """
    service = TelegramNotificationService(client=mock_telegram_client)
    res = service.send_user_notification(
        user=notification_setup["unlinked"],
        title="Alerte Sécurité",
        message="Connexion suspecte détectée."
    )
    assert res["status"] == "skipped"
    assert res["reason"] == "no_telegram_identity"
    mock_telegram_client.send_message.assert_not_called()

@pytest.mark.django_db
def test_send_user_notification_preference_filtering(mock_telegram_client, notification_setup):
    """
    Notifications matching a category disabled by the user must be skipped.
    """
    # Disable finance notifications for admin
    pref, _ = TelegramNotificationPreference.objects.get_or_create(identity=notification_setup["id_admin"])
    pref.alert_finance = False
    pref.save()

    service = TelegramNotificationService(client=mock_telegram_client)
    res = service.send_user_notification(
        user=notification_setup["admin"],
        title="Relance Paiement",
        message="Échéance dépassée.",
        category="finance"
    )

    assert res["status"] == "skipped"
    assert res["reason"] == "preference_disabled"
    mock_telegram_client.send_message.assert_not_called()

@pytest.mark.django_db
def test_send_user_notification_idempotency(mock_telegram_client, notification_setup):
    """
    Duplicate notifications with the same idempotency_key must not be sent twice.
    """
    service = TelegramNotificationService(client=mock_telegram_client)
    key = "unique_stock_alert_001"

    res1 = service.send_user_notification(
        user=notification_setup["admin"],
        title="Rupture de Stock",
        message="Article Cahier 200p épuisé.",
        category="inventory",
        idempotency_key=key
    )
    assert res1["status"] == "delivered"
    assert mock_telegram_client.send_message.call_count == 1

    # Second call with same key
    res2 = service.send_user_notification(
        user=notification_setup["admin"],
        title="Rupture de Stock",
        message="Article Cahier 200p épuisé.",
        category="inventory",
        idempotency_key=key
    )
    assert res2["status"] == "already_delivered"
    assert mock_telegram_client.send_message.call_count == 1

@pytest.mark.django_db
def test_send_organization_alert_with_role_filter(mock_telegram_client, notification_setup):
    """
    Organization alerts can broadcast to all members or target specific roles.
    """
    service = TelegramNotificationService(client=mock_telegram_client)

    # 1. Target all members in org
    res_all = service.send_organization_alert(
        organization=notification_setup["org"],
        title="Maintenance Système",
        message="Arrêt planifié ce soir à 23h.",
        category="system"
    )
    assert res_all["total_candidates"] == 2
    assert res_all["sent_count"] == 2
    assert mock_telegram_client.send_message.call_count == 2

    mock_telegram_client.send_message.reset_mock()

    # 2. Filter by role: only ADMINISTRATOR
    res_admin = service.send_organization_alert(
        organization=notification_setup["org"],
        title="Incident Critique",
        message="Incident de sécurité détecté.",
        level=TelegramNotificationLog.LEVEL_ALERT,
        category="security",
        role_filter=["ADMINISTRATOR"]
    )
    assert res_admin["total_candidates"] == 1
    assert res_admin["sent_count"] == 1
    assert mock_telegram_client.send_message.call_count == 1

@pytest.mark.django_db
def test_broadcast_channel_and_community(mock_telegram_client):
    """
    Broadcasting officially pushes to channel (@allianceonechannels) and community (@allianceonecommunity).
    """
    service = TelegramNotificationService(client=mock_telegram_client)

    # Broadcast to channel
    res_chan = service.broadcast_channel(
        title="Version 2.5 Déployée",
        message="Nouvelles fonctionnalités d'intelligence artificielle disponibles.",
        channel_id="@allianceonechannels"
    )
    assert res_chan["status"] == "delivered"
    assert res_chan["channel"] == "@allianceonechannels"
    args, kwargs = mock_telegram_client.send_message.call_args
    chan_target = kwargs.get("chat_id") or (args[0] if args else None)
    assert chan_target == "@allianceonechannels"
    assert "COMMUNIQUÉ OFFICIEL ALLIANCE ONE" in kwargs["text"]

    # Verify channel log in DB
    chan_log = TelegramNotificationLog.objects.get(recipient_type=TelegramNotificationLog.RECIPIENT_CHANNEL)
    assert chan_log.status == TelegramNotificationLog.STATUS_DELIVERED

    mock_telegram_client.send_message.reset_mock()

    # Broadcast to community
    res_comm = service.broadcast_community(
        title="Webinaire Vendredi 15h",
        message="Session de questions-réponses sur les nouveautés.",
        group_id="@allianceonecommunity"
    )
    assert res_comm["status"] == "delivered"
    assert res_comm["group"] == "@allianceonecommunity"
    args, kwargs = mock_telegram_client.send_message.call_args
    comm_target = kwargs.get("chat_id") or (args[0] if args else None)
    assert comm_target == "@allianceonecommunity"
    assert "COMMUNAUTÉ ALLIANCE ONE" in kwargs["text"]

@pytest.mark.django_db
def test_notification_bot_command_and_toggle(mock_telegram_client, notification_setup):
    """
    Command /alerts displays preferences keyboard, and callback query notif_pref: toggles setting in real-time.
    """
    # 1. Command /alerts
    msg_update = {
        "update_id": 101,
        "message": {
            "message_id": 50,
            "from": {"id": 111222, "first_name": "Admin"},
            "chat": {"id": 111222},
            "text": "/alerts"
        }
    }
    res_cmd = handle_update(msg_update, client=mock_telegram_client)
    assert res_cmd["status"] == "handled"
    assert res_cmd["command"] == "/alerts"
    mock_telegram_client.send_message.assert_called_once()
    args, kwargs = mock_telegram_client.send_message.call_args
    assert "Préférences d'Alertes Instantanées Telegram" in args[1]
    assert len(kwargs["reply_markup"]["inline_keyboard"]) == 6

    # 2. Callback query toggle: notif_pref:finance
    pref = TelegramNotificationPreference.objects.get(identity=notification_setup["id_admin"])
    assert pref.alert_finance is True

    cb_update = {
        "update_id": 102,
        "callback_query": {
            "id": "query_777",
            "from": {"id": 111222},
            "message": {
                "message_id": 50,
                "chat": {"id": 111222}
            },
            "data": "notif_pref:finance"
        }
    }
    res_cb = handle_update(cb_update, client=mock_telegram_client)
    assert res_cb["status"] == "handled"
    assert res_cb["action"] == "toggle_pref"
    assert res_cb["category"] == "finance"

    pref.refresh_from_db()
    assert pref.alert_finance is False
    mock_telegram_client.answer_callback_query.assert_called_with("query_777", text="Préférences mises à jour ✅")

@pytest.mark.django_db
def test_web_views_preferences_and_test_notification(notification_setup):
    """
    REST API endpoints allow web users to inspect and toggle preferences,
    and trigger a live test notification.
    """
    factory = APIRequestFactory()
    user = notification_setup["admin"]

    # 1. GET /api/integrations/telegram/preferences/
    request_get = factory.get('/api/integrations/telegram/preferences/')
    force_authenticate(request_get, user=user)
    view_prefs = TelegramPreferencesView.as_view()
    response_get = view_prefs(request_get)
    assert response_get.status_code == 200
    assert response_get.data["is_linked"] is True
    assert response_get.data["preferences"]["alert_security"] is True

    # 2. POST /api/integrations/telegram/preferences/
    request_post = factory.post('/api/integrations/telegram/preferences/', {
        "alert_inventory": False,
        "daily_digest": True
    }, format="json")
    force_authenticate(request_post, user=user)
    response_post = view_prefs(request_post)
    assert response_post.status_code == 200
    assert response_post.data["preferences"]["alert_inventory"] is False
    assert response_post.data["preferences"]["daily_digest"] is True

    # 3. POST /api/integrations/telegram/test-notification/
    with patch("platform_services.telegram.web_views.TelegramNotificationService.send_user_notification") as mock_send:
        mock_send.return_value = {"status": "delivered", "telegram_message_id": 888123}
        request_test = factory.post('/api/integrations/telegram/test-notification/', {}, format="json")
        force_authenticate(request_test, user=user)
        view_test = TelegramTestNotificationView.as_view()
        response_test = view_test(request_test)
        assert response_test.status_code == 200
        assert response_test.data["status"] == "success"
        assert "envoyée avec succès" in response_test.data["message"]
