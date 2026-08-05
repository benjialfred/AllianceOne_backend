import pytest
from rest_framework.test import APIClient
from platform_services.identity.models import Organization, Workspace

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def setup_tenants():
    org_a = Organization.objects.create(name="Org A")
    org_b = Organization.objects.create(name="Org B")
    
    Workspace.objects.create(name="Workspace A1", slug="ws-a1", organization=org_a)
    Workspace.objects.create(name="Workspace A2", slug="ws-a2", organization=org_a)
    Workspace.objects.create(name="Workspace B1", slug="ws-b1", organization=org_b)
    
    return org_a, org_b


@pytest.mark.django_db
def test_tenant_isolation_with_headers(api_client, setup_tenants):
    org_a, org_b = setup_tenants
    
    # Appel API sans header -> doit renvoyer 0 Workspace selon notre mixin (mock permissif/restrictif)
    response = api_client.get('/api/core/identity/workspaces/')
    assert response.status_code == 200
    assert len(response.data) == 0

    # Appel API avec header Org A
    response = api_client.get('/api/core/identity/workspaces/', HTTP_X_TENANT_ID=str(org_a.id))
    assert response.status_code == 200
    assert len(response.data) == 2
    assert response.data[0]['name'] == "Workspace A1"

    # Appel API avec header Org B
    response = api_client.get('/api/core/identity/workspaces/', HTTP_X_TENANT_ID=str(org_b.id))
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['name'] == "Workspace B1"
