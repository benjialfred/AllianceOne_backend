import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from platform_services.alliance_modules.models import Module, ModulePlan, ModuleInstallation, InstallationStatus
from platform_services.payments.models import AlliancePayment, PaymentStatus
from django.contrib.auth import get_user_model
from platform_services.identity.models import Organization
User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def setup_data(db):
    user = User.objects.create_user(email="test@alliance.one", password="password")
    org = Organization.objects.create(name="Test Org")
    
    # Create module and plan
    module = Module.objects.create(slug="test-module", name="Test Module", category="CORE")
    free_plan = ModulePlan.objects.create(module=module, name="Free", is_free=True, price_monthly=0)
    paid_plan = ModulePlan.objects.create(module=module, name="Premium", is_free=False, price_monthly=5000)
    
    return {
        "user": user,
        "org": org,
        "module": module,
        "free_plan": free_plan,
        "paid_plan": paid_plan
    }

@pytest.mark.django_db
def test_free_module_installation(api_client, setup_data):
    api_client.force_authenticate(user=setup_data["user"])
    # Attach org manually since middleware might not run in test isolation perfectly depending on setup
    user = setup_data["user"]
    
    from platform_services.identity.models import Membership, Role
    role = Role.objects.create(name="Admin", organization=setup_data["org"])
    Membership.objects.create(user=user, organization=setup_data["org"], role=role)

    url = reverse("module-install", kwargs={"slug": "test-module"})
    response = api_client.post(url, {"plan_id": setup_data["free_plan"].id})
    
    assert response.status_code == 201
    installation = ModuleInstallation.objects.get(organization=setup_data["org"], module=setup_data["module"])
    assert installation.status == InstallationStatus.ACTIVE

@pytest.mark.django_db
def test_paid_module_checkout_and_webhook_activation(api_client, setup_data):
    api_client.force_authenticate(user=setup_data["user"])
    user = setup_data["user"]
    org = setup_data["org"]
    
    from platform_services.identity.models import Membership, Role
    role = Role.objects.create(name="Admin", organization=org)
    Membership.objects.create(user=user, organization=org, role=role)
    from unittest.mock import patch
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "checkout_url": "https://nelsius.test/checkout/123",
            "reference": "NEL_REF_123"
        }
        mock_post.return_value.raise_for_status = lambda: None

        url = reverse("module-install", kwargs={"slug": "test-module"})
        response = api_client.post(url, {"plan_id": setup_data["paid_plan"].id})
        
        assert response.status_code == 200
    assert "checkout_url" in response.data
    merchant_reference = response.data["merchant_reference"]
    
    # Verify installation is PENDING
    installation = ModuleInstallation.objects.get(organization=org, module=setup_data["module"])
    assert installation.status == InstallationStatus.PENDING
    
    # Verify payment exists
    payment = AlliancePayment.objects.get(merchant_reference=merchant_reference)
    assert payment.status == PaymentStatus.CREATED
    
    # 2. Simulate Webhook
    webhook_url = reverse("payment-verify")
    webhook_payload = {
        "merchant_reference": merchant_reference,
        "transaction_id": "NEL_123456"
    }
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": {
                "status": "completed",
                "transaction_code": "NEL_123456"
            }
        }
        mock_get.return_value.raise_for_status = lambda: None
        
        webhook_resp = api_client.post(webhook_url, webhook_payload, format="json")
        assert webhook_resp.status_code == 200
    
    # 3. Verify Payment and Installation updated
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.COMPLETED
    assert payment.provider_transaction_code == "NEL_123456"
    
    installation.refresh_from_db()
    assert installation.status == InstallationStatus.ACTIVE
