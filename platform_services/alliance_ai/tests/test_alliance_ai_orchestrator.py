import pytest
from platform_services.alliance_ai.orchestration.state import ExecutionPlan, ExecutionStep, ExecutionStatus
from platform_services.alliance_ai.orchestration.orchestrator import AllianceAIOrchestrator, Planner, DependencyGraph
from platform_services.alliance_ai.context.context_schema import AllianceAIContext
from unittest.mock import MagicMock

def get_context():
    return AllianceAIContext(user_id="u1", user_email="a@a.com", organization_id="org1", organization_name="Org1")

def test_orchestrator_successful_flow():
    orchestrator = AllianceAIOrchestrator()
    
    # Mock Planner to return a plan with 2 steps
    def mock_create_plan(user_request, context):
        plan = ExecutionPlan(user_request, context.organization_id)
        step1 = ExecutionStep(tool_name="tool.a", arguments={})
        step2 = ExecutionStep(tool_name="tool.b", arguments={})
        plan.add_step(step1)
        plan.add_step(step2)
        return plan
        
    orchestrator.planner.create_plan = mock_create_plan
    
    context = get_context()
    plan = orchestrator.handle_request("do something", context)
    
    assert plan.status == ExecutionStatus.SUCCEEDED
    assert len(plan.steps) == 2
    assert plan.steps[0].status == ExecutionStatus.SUCCEEDED
    assert plan.steps[1].status == ExecutionStatus.SUCCEEDED

def test_orchestrator_verification_failure():
    orchestrator = AllianceAIOrchestrator()
    
    def mock_create_plan(user_request, context):
        plan = ExecutionPlan(user_request, context.organization_id)
        plan.add_step(ExecutionStep(tool_name="tool.a", arguments={}))
        return plan
        
    orchestrator.planner.create_plan = mock_create_plan
    
    # Mock Verifier to fail
    orchestrator.verifier.verify = MagicMock(return_value=False)
    
    context = get_context()
    plan = orchestrator.handle_request("do something", context)
    
    assert plan.status == ExecutionStatus.FAILED
    assert plan.steps[0].status == ExecutionStatus.VERIFICATION_FAILED

def test_orchestrator_waiting_for_approval():
    orchestrator = AllianceAIOrchestrator()
    
    def mock_create_plan(user_request, context):
        plan = ExecutionPlan(user_request, context.organization_id)
        plan.add_step(ExecutionStep(tool_name="tool.a", arguments={}))
        return plan
        
    orchestrator.planner.create_plan = mock_create_plan
    
    # Mock Executor to require approval
    def mock_execute(step, plan, context):
        step.status = ExecutionStatus.WAITING_FOR_APPROVAL
        return step
    orchestrator.executor.execute = mock_execute
    
    context = get_context()
    plan = orchestrator.handle_request("do something", context)
    
    assert plan.status == ExecutionStatus.WAITING_FOR_APPROVAL
    assert plan.steps[0].status == ExecutionStatus.WAITING_FOR_APPROVAL
    
    # Simulate user approval -> set back to PENDING and mock execute to succeed
    plan.steps[0].status = ExecutionStatus.PENDING
    orchestrator.executor.execute = lambda s, p, c: setattr(s, 'status', ExecutionStatus.SUCCEEDED) or s
    
    resumed_plan = orchestrator.resume_plan(plan, context)
    assert resumed_plan.status == ExecutionStatus.SUCCEEDED
    assert resumed_plan.steps[0].status == ExecutionStatus.SUCCEEDED
