import pytest
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from platform_services.identity.models import Organization, Role, Membership
from platform_services.telegram.models import TelegramIdentity
from platform_services.telegram.handlers import handle_update, handle_message, handle_callback_query
from platform_services.telegram.client import TelegramClient
from platform_services.telegram.ai_service import process_ai_query, UNAUTHENTICATED_AI_MESSAGE
from platform_services.alliance_ai.orchestration.state import ExecutionPlan, ExecutionStep, ExecutionStatus
from platform_services.alliance_ai.orchestration.state_store import StateStore
from platform_services.alliance_ai.security.types import generate_canonical_action_hash

User = get_user_model()

@pytest.fixture
def mock_telegram_client():
    client = MagicMock(spec=TelegramClient)
    client.send_message.return_value = {"message_id": 123, "ok": True}
    client.edit_message_text.return_value = {"message_id": 123, "ok": True}
    client.send_chat_action.return_value = {"ok": True}
    client.answer_callback_query.return_value = {"ok": True}
    return client

@pytest.fixture
def ai_test_setup(db):
    user = User.objects.create(email="ai_user@example.com")
    org = Organization.objects.create(name="Alliance AI College", active_modules=["education", "finance", "inventory"])
    role = Role.objects.create(name="ADMINISTRATOR", organization=org)
    membership = Membership.objects.create(user=user, organization=org, role=role)
    identity = TelegramIdentity.objects.create(
        telegram_user_id=888999,
        telegram_chat_id=888999,
        user=user,
        active_organization=org,
        is_active=True
    )
    return {
        "user": user,
        "org": org,
        "role": role,
        "membership": membership,
        "identity": identity
    }

@pytest.mark.django_db
def test_unauthenticated_ai_query_blocked(mock_telegram_client):
    """
    Unlinked users attempting to ask questions must be blocked fail-closed
    and prompted to connect their Alliance One account.
    """
    update = {
        "update_id": 9001,
        "message": {
            "message_id": 1,
            "from": {"id": 999999, "first_name": "Stranger"},
            "chat": {"id": 999999},
            "text": "Comment fonctionne l'ERP ?"
        }
    }
    result = handle_update(update, client=mock_telegram_client)
    assert result["status"] == "unauthenticated"
    mock_telegram_client.send_message.assert_called_once()
    args, kwargs = mock_telegram_client.send_message.call_args
    assert args[0] == 999999
    assert "Authentification requise" in args[1]

@pytest.mark.django_db
def test_ai_query_no_active_org(mock_telegram_client):
    """
    A linked user whose active organization/membership is missing must be notified.
    """
    user = User.objects.create(email="no_org@example.com")
    TelegramIdentity.objects.create(
        telegram_user_id=777888,
        telegram_chat_id=777888,
        user=user,
        active_organization=None,
        is_active=True
    )

    update = {
        "update_id": 9002,
        "message": {
            "message_id": 2,
            "from": {"id": 777888},
            "chat": {"id": 777888},
            "text": "Donne-moi les stats"
        }
    }
    result = handle_update(update, client=mock_telegram_client)
    assert result["status"] == "no_active_organization"
    mock_telegram_client.send_message.assert_called_once()
    assert "Aucune organisation active" in mock_telegram_client.send_message.call_args[0][1]

@pytest.mark.django_db
def test_ai_fast_track_conversational_chat(ai_test_setup, mock_telegram_client):
    """
    A linked user asking a conversational question gets fast-tracked without delay.
    Native typing action is emitted and clean response returned.
    """
    with patch("platform_services.telegram.ai_service.AllianceAIGateway.ask") as mock_ask:
        mock_ask.return_value = {
            "status": "SUCCESS",
            "plan_id": None,
            "content": "Bonjour ! Je suis Alliance AI, votre copilote opérationnel.",
            "data": {"type": "chat", "content": "Bonjour ! Je suis Alliance AI, votre copilote opérationnel."}
        }

        update = {
            "update_id": 9003,
            "message": {
                "message_id": 3,
                "from": {"id": 888999},
                "chat": {"id": 888999},
                "text": "Bonjour, que peux-tu faire ?"
            }
        }
        result = handle_update(update, client=mock_telegram_client)
        assert result["status"] == "success"
        assert result["type"] == "chat"

        # Verify typing action was emitted
        mock_telegram_client.send_chat_action.assert_called_with(888999, "typing")

        # Verify gateway was called with secure client context
        mock_ask.assert_called_once()
        _, kwargs = mock_ask.call_args
        assert kwargs["user"] == ai_test_setup["user"]
        assert kwargs["prompt"] == "Bonjour, que peux-tu faire ?"
        assert kwargs["client_context"]["organization_id"] == str(ai_test_setup["org"].id)
        assert kwargs["client_context"]["source"] == "telegram"

        # Verify response sent to user
        mock_telegram_client.send_message.assert_called_once()
        assert "Alliance AI" in mock_telegram_client.send_message.call_args[0][1]

@pytest.mark.django_db
def test_ai_command_routing(ai_test_setup, mock_telegram_client):
    """
    Explicit /ai command strips prefix and forwards query to Gateway.
    """
    with patch("platform_services.telegram.ai_service.AllianceAIGateway.ask") as mock_ask:
        mock_ask.return_value = {
            "status": "SUCCESS",
            "plan_id": None,
            "content": "Voici les informations demandées.",
            "data": {"type": "chat"}
        }

        update = {
            "update_id": 9004,
            "message": {
                "message_id": 4,
                "from": {"id": 888999},
                "chat": {"id": 888999},
                "text": "/ai Quels sont les modules installés ?"
            }
        }
        result = handle_update(update, client=mock_telegram_client)
        assert result["status"] == "success"
        mock_ask.assert_called_once()
        assert mock_ask.call_args[1]["prompt"] == "Quels sont les modules installés ?"

@pytest.mark.django_db
def test_ai_sensitive_action_requires_confirmation(ai_test_setup, mock_telegram_client):
    """
    A sensitive action requiring human approval pauses and presents an authorization
    inline keyboard with the canonical action hash.
    """
    plan = ExecutionPlan(
        user_request="Mettre à jour le stock de cahiers",
        organization_id=str(ai_test_setup["org"].id),
        plan_id="plan_test_001"
    )
    step = ExecutionStep(
        tool_name="inventory.update_stock",
        arguments={"product_id": "prod_cahier_01", "quantity": 50},
        step_id="step_test_001"
    )
    step.status = ExecutionStatus.WAITING_FOR_APPROVAL
    step.requires_confirmation = True
    action_hash = generate_canonical_action_hash(
        mission_id="plan_test_001",
        organization_id=str(ai_test_setup["org"].id),
        user_id=str(ai_test_setup["user"].id),
        tool_name="inventory.update_stock",
        arguments={"product_id": "prod_cahier_01", "quantity": 50}
    )
    step.execution_metadata["action_hash"] = action_hash
    plan.add_step(step)
    plan.status = ExecutionStatus.WAITING_FOR_APPROVAL
    StateStore.save_plan(plan)

    with patch("platform_services.telegram.ai_service.AllianceAIGateway.ask") as mock_ask:
        mock_ask.return_value = {
            "status": "SUCCESS",
            "plan_id": "plan_test_001",
            "content": "Je prépare l'action...",
            "data": {
                "type": "mission_plan",
                "mission": {"status": "WAITING_FOR_APPROVAL"}
            }
        }

        update = {
            "update_id": 9005,
            "message": {
                "message_id": 5,
                "from": {"id": 888999},
                "chat": {"id": 888999},
                "text": "Ajuste le stock de cahiers à 50"
            }
        }
        result = handle_update(update, client=mock_telegram_client)
        assert result["status"] == "waiting_approval"
        assert result["action_hash"] == action_hash

        mock_telegram_client.send_message.assert_called_once()
        msg_text = mock_telegram_client.send_message.call_args[0][1]
        reply_markup = mock_telegram_client.send_message.call_args[1]["reply_markup"]

        assert "Demande d'Autorisation Sécurisée" in msg_text
        assert "inventory.update_stock" in msg_text
        # Verify callback data contains plan_id, step_id, and action_hash
        confirm_btn = reply_markup["inline_keyboard"][0][0]
        assert confirm_btn["text"] == "✅ Confirmer l'action"
        assert confirm_btn["callback_data"] == f"ai_confirm:plan_test_001:step_test_001:{action_hash}"

@pytest.mark.django_db
def test_ai_confirm_callback_authorized_and_verified(ai_test_setup, mock_telegram_client):
    """
    Clicking confirm revalidates canonical action hash and executes the step
    with post-execution verification.
    """
    from platform_services.inventory.ai_tools import register_inventory_tools
    register_inventory_tools()

    plan = ExecutionPlan(
        user_request="Mise à jour stock",
        organization_id=str(ai_test_setup["org"].id),
        plan_id="plan_confirm_001"
    )
    step = ExecutionStep(
        tool_name="inventory.update_stock",
        arguments={"product_id": "prod_99", "quantity": 10},
        step_id="step_confirm_001"
    )
    step.status = ExecutionStatus.WAITING_FOR_APPROVAL
    step.requires_confirmation = True
    action_hash = generate_canonical_action_hash(
        mission_id="plan_confirm_001",
        organization_id=str(ai_test_setup["org"].id),
        user_id=str(ai_test_setup["user"].id),
        tool_name="inventory.update_stock",
        arguments={"product_id": "prod_99", "quantity": 10}
    )
    step.execution_metadata["action_hash"] = action_hash
    plan.add_step(step)
    plan.status = ExecutionStatus.WAITING_FOR_APPROVAL
    StateStore.save_plan(plan)

    callback_update = {
        "update_id": 9006,
        "callback_query": {
            "id": "query_confirm_1",
            "from": {"id": 888999},
            "message": {
                "message_id": 10,
                "chat": {"id": 888999}
            },
            "data": f"ai_confirm:plan_confirm_001:step_confirm_001:{action_hash}"
        }
    }

    result = handle_update(callback_update, client=mock_telegram_client)
    assert result["status"] == "success"
    assert result["executed"] is True

    # Check updated plan in DB
    updated_plan = StateStore.load_plan("plan_confirm_001")
    updated_step = updated_plan.get_step("step_confirm_001")
    assert updated_step.status == ExecutionStatus.SUCCEEDED
    assert updated_step.verification_status == "VERIFIED"

    # Verify message was edited to show success
    mock_telegram_client.edit_message_text.assert_called_once()
    edit_text = mock_telegram_client.edit_message_text.call_args[1]["text"]
    assert "Exécutée avec Succès" in edit_text
    assert "inventory.update_stock" in edit_text

@pytest.mark.django_db
def test_ai_confirm_callback_tampered_hash_rejected(ai_test_setup, mock_telegram_client):
    """
    Submitting an altered action hash must be rejected by the Security Gate.
    """
    plan = ExecutionPlan(
        user_request="Mise à jour stock",
        organization_id=str(ai_test_setup["org"].id),
        plan_id="plan_tamper_001"
    )
    step = ExecutionStep(
        tool_name="inventory.update_stock",
        arguments={"product_id": "prod_99", "quantity": 10},
        step_id="step_tamper_001"
    )
    step.status = ExecutionStatus.WAITING_FOR_APPROVAL
    step.requires_confirmation = True
    real_hash = generate_canonical_action_hash(
        mission_id="plan_tamper_001",
        organization_id=str(ai_test_setup["org"].id),
        user_id=str(ai_test_setup["user"].id),
        tool_name="inventory.update_stock",
        arguments={"product_id": "prod_99", "quantity": 10}
    )
    step.execution_metadata["action_hash"] = real_hash
    plan.add_step(step)
    plan.status = ExecutionStatus.WAITING_FOR_APPROVAL
    StateStore.save_plan(plan)

    fake_hash = "tampered_fake_hash_12345"
    callback_update = {
        "update_id": 9007,
        "callback_query": {
            "id": "query_tamper_1",
            "from": {"id": 888999},
            "message": {
                "message_id": 11,
                "chat": {"id": 888999}
            },
            "data": f"ai_confirm:plan_tamper_001:step_tamper_001:{fake_hash}"
        }
    }

    result = handle_update(callback_update, client=mock_telegram_client)
    assert result["status"] == "security_deny"
    assert result["reason"] == "ACTION_HASH_MISMATCH"

    mock_telegram_client.answer_callback_query.assert_called_with(
        "query_tamper_1",
        text="Refus de sécurité : ACTION_HASH_MISMATCH",
        show_alert=True
    )

@pytest.mark.django_db
def test_ai_cancel_callback(ai_test_setup, mock_telegram_client):
    """
    Clicking 'Annuler' marks the step as cancelled and informs the user.
    """
    plan = ExecutionPlan(
        user_request="Mise à jour",
        organization_id=str(ai_test_setup["org"].id),
        plan_id="plan_cancel_001"
    )
    step = ExecutionStep(
        tool_name="inventory.update_stock",
        arguments={"product_id": "prod_99", "quantity": 10},
        step_id="step_cancel_001"
    )
    step.status = ExecutionStatus.WAITING_FOR_APPROVAL
    plan.add_step(step)
    StateStore.save_plan(plan)

    callback_update = {
        "update_id": 9008,
        "callback_query": {
            "id": "query_cancel_1",
            "from": {"id": 888999},
            "message": {
                "message_id": 12,
                "chat": {"id": 888999}
            },
            "data": "ai_cancel:plan_cancel_001:step_cancel_001"
        }
    }

    result = handle_update(callback_update, client=mock_telegram_client)
    assert result["status"] == "cancelled"

    updated_plan = StateStore.load_plan("plan_cancel_001")
    assert updated_plan.status == ExecutionStatus.FAILED
    assert updated_plan.get_step("step_cancel_001").status == ExecutionStatus.FAILED

    mock_telegram_client.edit_message_text.assert_called_once()
    assert "Action annulée" in mock_telegram_client.edit_message_text.call_args[1]["text"]

@pytest.mark.django_db
def test_ai_gateway_error_resilience(ai_test_setup, mock_telegram_client):
    """
    When Gateway returns an error, Telegram bot handles it smoothly.
    """
    with patch("platform_services.telegram.ai_service.AllianceAIGateway.ask") as mock_ask:
        mock_ask.return_value = {
            "status": "ERROR",
            "content": "Service temporairement indisponible."
        }

        update = {
            "update_id": 9009,
            "message": {
                "message_id": 6,
                "from": {"id": 888999},
                "chat": {"id": 888999},
                "text": "Question qui échoue"
            }
        }
        result = handle_update(update, client=mock_telegram_client)
        assert result["status"] == "gateway_error"
        mock_telegram_client.send_message.assert_called_once()
        assert "Erreur Alliance AI" in mock_telegram_client.send_message.call_args[0][1]
