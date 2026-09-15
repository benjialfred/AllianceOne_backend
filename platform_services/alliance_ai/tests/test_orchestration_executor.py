import pytest
from platform_services.alliance_ai.orchestration.state import ExecutionPlan, ExecutionStep, ExecutionStatus
from platform_services.alliance_ai.orchestration.executor import StepExecutor
from platform_services.alliance_ai.context.context_schema import AllianceAIContext
from platform_services.alliance_ai.security.types import Decision, ApprovalDecision
from platform_services.alliance_ai.tools.definitions import RiskLevel
from unittest.mock import patch, MagicMock

def get_context():
    return AllianceAIContext(user_id="u1", user_email="a@a.com", organization_id="org1", organization_name="Org1")

def test_argument_resolution():
    executor = StepExecutor()
    plan = ExecutionPlan("test", "org")
    
    s1 = ExecutionStep(tool_name="a", arguments={}, step_id="step_1")
    s1.status = ExecutionStatus.SUCCEEDED
    s1.output = {"id": 42, "user": {"name": "Alice"}}
    plan.add_step(s1)
    
    s2 = ExecutionStep(tool_name="b", arguments={
        "single_ref": "{{step_1.output.id}}",
        "nested_ref": "{{step_1.output.user.name}}",
        "mixed_string": "User ID is {{step_1.output.id}}",
        "list_ref": ["{{step_1.output.id}}", "static"]
    }, step_id="step_2")
    plan.add_step(s2)
    
    resolved = executor._resolve_arguments(s2.arguments, plan)
    
    assert resolved["single_ref"] == 42 # Preserves type for exact match
    assert resolved["nested_ref"] == "Alice"
    assert resolved["mixed_string"] == "User ID is 42"
    assert resolved["list_ref"] == [42, "static"]

def test_argument_resolution_fails_if_step_not_succeeded():
    executor = StepExecutor()
    plan = ExecutionPlan("test", "org")
    
    s1 = ExecutionStep(tool_name="a", arguments={}, step_id="step_1")
    s1.status = ExecutionStatus.FAILED
    plan.add_step(s1)
    
    s2 = ExecutionStep(tool_name="b", arguments={"ref": "{{step_1.output.id}}"}, step_id="step_2")
    plan.add_step(s2)
    
    with pytest.raises(ValueError):
        executor._resolve_arguments(s2.arguments, plan)

@pytest.mark.django_db
@patch("platform_services.alliance_ai.orchestration.state_store.StateStore.save_plan")
@patch("platform_services.alliance_ai.orchestration.executor.ToolRegistry.execute_tool")
@patch("platform_services.alliance_ai.orchestration.executor.SecurityApprovalEngine.evaluate")
def test_executor_full_flow(mock_evaluate, mock_execute, mock_save_plan):
    executor = StepExecutor()
    plan = ExecutionPlan("test", "org")
    s1 = ExecutionStep(tool_name="a", arguments={"arg1": "val1"}, step_id="step_1")
    plan.add_step(s1)
    
    mock_evaluate.return_value = ApprovalDecision(
        decision=Decision.ALLOW,
        requires_confirmation=False,
        reason="",
        risk_level=RiskLevel.LOW,
        policy="",
        user_id="u1",
        organization_id="org1",
        tool="a"
    )
    mock_execute.return_value = {"success": True}
    
    context = get_context()
    result_step = executor.execute(s1, plan, context)
    
    assert result_step.status == ExecutionStatus.SUCCEEDED
    assert result_step.output == {"success": True}
    mock_execute.assert_called_once_with("a", {"arg1": "val1"}, context)

@pytest.mark.django_db
@patch("platform_services.alliance_ai.orchestration.state_store.StateStore.save_plan")
@patch("platform_services.alliance_ai.orchestration.executor.SecurityApprovalEngine.evaluate")
def test_executor_security_deny(mock_evaluate, mock_save_plan):
    executor = StepExecutor()
    plan = ExecutionPlan("test", "org")
    s1 = ExecutionStep(tool_name="a", arguments={"arg1": "val1"}, step_id="step_1")
    plan.add_step(s1)
    
    mock_evaluate.return_value = ApprovalDecision(
        decision=Decision.DENY,
        requires_confirmation=False,
        reason="No",
        risk_level=RiskLevel.LOW,
        policy="",
        user_id="u1",
        organization_id="org1",
        tool="a",
        reason_code="DENIED"
    )
    
    context = get_context()
    result_step = executor.execute(s1, plan, context)
    
    assert result_step.status == ExecutionStatus.FAILED
    assert "SECURITY_DENY" in result_step.error
