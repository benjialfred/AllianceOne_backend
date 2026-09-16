import pytest
from unittest.mock import MagicMock, patch
from platform_services.alliance_ai.orchestration.state import ExecutionPlan, ExecutionStep, ExecutionStatus
from platform_services.alliance_ai.orchestration.orchestrator import AllianceAIOrchestrator
from platform_services.alliance_ai.context.context_schema import AllianceAIContext

def get_context():
    # Use valid UUID for organization_id to satisfy SecurityGate
    return AllianceAIContext(
        user_id="u1", 
        user_email="a@a.com", 
        organization_id="b7e52a92-628b-4b14-8f19-35a22d4f820c", 
        organization_name="Test Organization"
    )

@pytest.mark.django_db
def test_orchestrator_fast_track_chat():
    """Verify that simple questions/chat with 0 steps bypass background execution and return immediately."""
    orchestrator = AllianceAIOrchestrator()
    
    def mock_create_chat_plan(user_request, context, history=None):
        plan = ExecutionPlan(user_request, context.organization_id)
        plan.plan_type = "chat"
        plan.user_request_response = "Bonjour ! Je suis Alliance AI, prêt à vous aider."
        return plan
        
    orchestrator.planner.create_plan = mock_create_chat_plan
    
    context = get_context()
    plan = orchestrator.handle_request("Bonjour, comment vas-tu ?", context)
    
    assert plan.status == ExecutionStatus.SUCCEEDED
    assert plan.plan_type == "chat"
    assert len(plan.steps) == 0
    assert "Bonjour" in plan.user_request_response

@pytest.mark.django_db
def test_orchestrator_successful_flow():
    """Verify that missions with tools execute their steps."""
    orchestrator = AllianceAIOrchestrator()
    
    def mock_create_plan(user_request, context, history=None):
        plan = ExecutionPlan(user_request, context.organization_id)
        plan.plan_type = "mission_plan"
        step1 = ExecutionStep(tool_name="tool.a", arguments={})
        step2 = ExecutionStep(tool_name="tool.b", arguments={})
        plan.add_step(step1)
        plan.add_step(step2)
        return plan
        
    orchestrator.planner.create_plan = mock_create_plan
    # Mock executor and verifier to succeed
    orchestrator.executor.execute = lambda s, p, c: setattr(s, 'status', ExecutionStatus.SUCCEEDED) or s
    orchestrator.verifier.verify = MagicMock(return_value=True)
    
    context = get_context()
    with patch('platform_services.alliance_ai.tasks.run_execution_loop_task.delay') as mock_delay:
        mock_delay.side_effect = Exception("Test Celery Offline")
        plan = orchestrator.handle_request("do something", context)
    
    assert plan.status == ExecutionStatus.SUCCEEDED
    assert len(plan.steps) == 2
    assert plan.steps[0].status == ExecutionStatus.SUCCEEDED
    assert plan.steps[1].status == ExecutionStatus.SUCCEEDED

@pytest.mark.django_db
def test_orchestrator_verification_failure():
    """Verify that failed step verification halts the mission."""
    orchestrator = AllianceAIOrchestrator()
    
    def mock_create_plan(user_request, context, history=None):
        plan = ExecutionPlan(user_request, context.organization_id)
        plan.plan_type = "mission_plan"
        plan.add_step(ExecutionStep(tool_name="tool.a", arguments={}))
        return plan
        
    orchestrator.planner.create_plan = mock_create_plan
    orchestrator.executor.execute = lambda s, p, c: setattr(s, 'status', ExecutionStatus.SUCCEEDED) or s
    
    # Mock Verifier to fail
    orchestrator.verifier.verify = MagicMock(return_value=False)
    
    context = get_context()
    with patch('platform_services.alliance_ai.tasks.run_execution_loop_task.delay') as mock_delay:
        mock_delay.side_effect = Exception("Test Celery Offline")
        plan = orchestrator.handle_request("do something", context)
    
    assert plan.status == ExecutionStatus.FAILED
    assert plan.steps[0].status == ExecutionStatus.VERIFICATION_FAILED

@pytest.mark.django_db
def test_orchestrator_waiting_for_approval():
    """Verify that approval-requiring steps pause the plan until resumed."""
    orchestrator = AllianceAIOrchestrator()
    
    def mock_create_plan(user_request, context, history=None):
        plan = ExecutionPlan(user_request, context.organization_id)
        plan.plan_type = "mission_plan"
        plan.add_step(ExecutionStep(tool_name="tool.a", arguments={}))
        return plan
        
    orchestrator.planner.create_plan = mock_create_plan
    
    # Mock Executor to require approval
    def mock_execute(step, plan, context):
        step.status = ExecutionStatus.WAITING_FOR_APPROVAL
        return step
    orchestrator.executor.execute = mock_execute
    
    context = get_context()
    with patch('platform_services.alliance_ai.tasks.run_execution_loop_task.delay') as mock_delay:
        mock_delay.side_effect = Exception("Test Celery Offline")
        plan = orchestrator.handle_request("do something", context)
    
    assert plan.status == ExecutionStatus.WAITING_FOR_APPROVAL
    assert plan.steps[0].status == ExecutionStatus.WAITING_FOR_APPROVAL
    
    # Simulate user approval -> set back to PENDING, mock executor and verifier to succeed
    plan.steps[0].status = ExecutionStatus.PENDING
    orchestrator.executor.execute = lambda s, p, c: setattr(s, 'status', ExecutionStatus.SUCCEEDED) or s
    orchestrator.verifier.verify = MagicMock(return_value=True)
    
    resumed_plan = orchestrator.resume_plan(plan, context)
    assert resumed_plan.status == ExecutionStatus.SUCCEEDED
    assert resumed_plan.steps[0].status == ExecutionStatus.SUCCEEDED
