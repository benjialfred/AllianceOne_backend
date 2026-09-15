import pytest
from unittest.mock import patch, MagicMock

from platform_services.alliance_ai.security.approval_engine import SecurityApprovalEngine
from platform_services.alliance_ai.security.types import Decision, RiskLevel, ActionScope
from platform_services.alliance_ai.tools.definitions import AIToolPolicy
from platform_services.alliance_ai.context.context_schema import AllianceAIContext

# Mock Tools for testing
mock_tool = AIToolPolicy(
    name="test.read_data",
    description="Reads some data",
    input_schema={},
    output_schema={},
    required_permissions=["data.read"],
    risk_level=RiskLevel.LOW,
    action_scope=ActionScope.READ,
    mutation=False,
    requires_confirmation=False,
    object_scope="organization",
    handler=lambda **k: "ok"
)

mock_critical_tool = AIToolPolicy(
    name="test.delete_data",
    description="Deletes data",
    input_schema={},
    output_schema={},
    required_permissions=["data.delete"],
    risk_level=RiskLevel.CRITICAL,
    action_scope=ActionScope.DELETE,
    mutation=True,
    requires_confirmation=True,
    object_scope="organization",
    handler=lambda **k: "ok"
)

def get_mock_context(user_id="user_1", org_id="org_1"):
    return AllianceAIContext(
        user_id=user_id,
        user_email="test@example.com",
        organization_id=org_id,
        organization_name="Test Org"
    )

@patch("platform_services.alliance_ai.security.approval_engine.ToolRegistry.get_tool")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_membership")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_permissions")
def test_authentication_required(mock_perms, mock_membership, mock_get_tool):
    context = get_mock_context(user_id=None, org_id=None)
    decision = SecurityApprovalEngine.evaluate("test.read_data", {}, context)
    assert decision.decision == Decision.DENY
    assert decision.reason_code == "UNAUTHENTICATED"

@patch("platform_services.alliance_ai.security.approval_engine.ToolRegistry.get_tool")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_membership")
def test_membership_required(mock_membership, mock_get_tool):
    mock_membership.return_value = None
    context = get_mock_context()
    decision = SecurityApprovalEngine.evaluate("test.read_data", {}, context)
    assert decision.decision == Decision.DENY
    assert decision.reason_code == "MEMBERSHIP_NOT_FOUND"

@patch("platform_services.alliance_ai.security.approval_engine.ToolRegistry.get_tool")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_membership")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_permissions")
def test_permission_denied(mock_perms, mock_membership, mock_get_tool):
    mock_membership.return_value = MagicMock()
    mock_perms.return_value = [] # Missing 'data.read'
    mock_get_tool.return_value = mock_tool
    
    context = get_mock_context()
    decision = SecurityApprovalEngine.evaluate("test.read_data", {}, context)
    assert decision.decision == Decision.DENY
    assert decision.reason_code == "PERMISSION_DENIED"

@patch("platform_services.alliance_ai.security.approval_engine.ToolRegistry.get_tool")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_membership")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_permissions")
def test_tenant_mismatch(mock_perms, mock_membership, mock_get_tool):
    mock_membership.return_value = MagicMock()
    mock_perms.return_value = ["data.read"]
    mock_get_tool.return_value = mock_tool
    
    context = get_mock_context(org_id="org_1")
    # Trying to read for org_2
    decision = SecurityApprovalEngine.evaluate("test.read_data", {"organization_id": "org_2"}, context)
    assert decision.decision == Decision.DENY
    assert decision.reason_code == "TENANT_MISMATCH"

@patch("platform_services.alliance_ai.security.approval_engine.ToolRegistry.get_tool")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_membership")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_permissions")
def test_allow_safe_action(mock_perms, mock_membership, mock_get_tool):
    mock_membership.return_value = MagicMock()
    mock_perms.return_value = ["data.read"]
    mock_get_tool.return_value = mock_tool
    
    context = get_mock_context(org_id="org_1")
    decision = SecurityApprovalEngine.evaluate("test.read_data", {"organization_id": "org_1"}, context)
    assert decision.decision == Decision.ALLOW
    assert not decision.requires_confirmation

@patch("platform_services.alliance_ai.security.approval_engine.ToolRegistry.get_tool")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_membership")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_permissions")
def test_require_confirmation_for_critical(mock_perms, mock_membership, mock_get_tool):
    mock_membership.return_value = MagicMock()
    mock_perms.return_value = ["data.delete"]
    mock_get_tool.return_value = mock_critical_tool
    
    context = get_mock_context(org_id="org_1")
    decision = SecurityApprovalEngine.evaluate("test.delete_data", {"id": 42}, context)
    assert decision.decision == Decision.REQUIRE_CONFIRMATION
    assert decision.requires_confirmation
    assert decision.action_hash is not None

@patch("platform_services.alliance_ai.security.approval_engine.ToolRegistry.get_tool")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_membership")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_permissions")
def test_revalidate_confirmation_success(mock_perms, mock_membership, mock_get_tool):
    mock_membership.return_value = MagicMock()
    mock_perms.return_value = ["data.delete"]
    mock_get_tool.return_value = mock_critical_tool
    
    context = get_mock_context()
    decision1 = SecurityApprovalEngine.evaluate("test.delete_data", {"id": 42}, context)
    
    # Revalidate with correct hash
    decision2 = SecurityApprovalEngine.revalidate_confirmation("test.delete_data", {"id": 42}, context, "default", decision1.action_hash)
    assert decision2.decision == Decision.ALLOW

@patch("platform_services.alliance_ai.security.approval_engine.ToolRegistry.get_tool")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_membership")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_permissions")
def test_revalidate_confirmation_hash_mismatch(mock_perms, mock_membership, mock_get_tool):
    mock_membership.return_value = MagicMock()
    mock_perms.return_value = ["data.delete"]
    mock_get_tool.return_value = mock_critical_tool
    
    context = get_mock_context()
    decision1 = SecurityApprovalEngine.evaluate("test.delete_data", {"id": 42}, context)
    
    # Arguments altered! (id: 43 instead of 42)
    decision2 = SecurityApprovalEngine.revalidate_confirmation("test.delete_data", {"id": 43}, context, "default", decision1.action_hash)
    assert decision2.decision == Decision.DENY
    assert decision2.reason_code == "ACTION_HASH_MISMATCH"

@patch("platform_services.alliance_ai.security.approval_engine.ToolRegistry.get_tool")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_membership")
@patch("platform_services.alliance_ai.security.permission_resolver.PermissionResolver.resolve_permissions")
def test_revalidate_confirmation_permission_lost(mock_perms, mock_membership, mock_get_tool):
    mock_membership.return_value = MagicMock()
    mock_perms.return_value = ["data.delete"]
    mock_get_tool.return_value = mock_critical_tool
    
    context = get_mock_context()
    decision1 = SecurityApprovalEngine.evaluate("test.delete_data", {"id": 42}, context)
    
    # User loses permission before executing!
    mock_perms.return_value = [] 
    decision2 = SecurityApprovalEngine.revalidate_confirmation("test.delete_data", {"id": 42}, context, "default", decision1.action_hash)
    assert decision2.decision == Decision.DENY
    assert decision2.reason_code == "PERMISSION_DENIED"

def test_invented_tool():
    # If ToolRegistry raises ValueError for unknown tool
    context = get_mock_context()
    decision = SecurityApprovalEngine.evaluate("delete_everything", {}, context)
    assert decision.decision == Decision.DENY
    assert decision.reason_code == "UNKNOWN_TOOL"
