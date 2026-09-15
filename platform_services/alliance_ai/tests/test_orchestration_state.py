import pytest
from platform_services.alliance_ai.orchestration.state import ExecutionPlan, ExecutionStep, ExecutionStatus

def test_execution_step_creation():
    step = ExecutionStep(
        tool_name="test.tool",
        arguments={"a": 1}
    )
    assert step.step_id.startswith("step_")
    assert step.status == ExecutionStatus.PENDING
    assert step.tool_name == "test.tool"
    assert step.arguments == {"a": 1}
    assert step.dependencies == []

def test_execution_plan_creation():
    plan = ExecutionPlan(
        user_request="Do something",
        organization_id="org_123"
    )
    assert plan.plan_id.startswith("plan_")
    assert plan.status == ExecutionStatus.PENDING
    assert plan.user_request == "Do something"
    assert len(plan.steps) == 0

def test_plan_add_and_retrieve_steps():
    plan = ExecutionPlan(user_request="Test", organization_id="org_1")
    
    step1 = ExecutionStep(tool_name="tool.a", arguments={})
    step2 = ExecutionStep(tool_name="tool.b", arguments={})
    step2.status = ExecutionStatus.SUCCEEDED
    
    plan.add_step(step1)
    plan.add_step(step2)
    
    assert len(plan.steps) == 2
    
    # Retrieve by ID
    retrieved_step = plan.get_step(step1.step_id)
    assert retrieved_step is not None
    assert retrieved_step.tool_name == "tool.a"
    
    # Retrieve by status
    pending_steps = plan.get_steps_by_status(ExecutionStatus.PENDING)
    assert len(pending_steps) == 1
    assert pending_steps[0].step_id == step1.step_id
    
    succeeded_steps = plan.get_steps_by_status(ExecutionStatus.SUCCEEDED)
    assert len(succeeded_steps) == 1
    assert succeeded_steps[0].step_id == step2.step_id

def test_state_serialization():
    plan = ExecutionPlan(user_request="Test", organization_id="org_1")
    step = ExecutionStep(tool_name="tool.a", arguments={"b": 2})
    plan.add_step(step)
    
    data = plan.to_dict()
    assert data["plan_id"] == plan.plan_id
    assert data["organization_id"] == "org_1"
    assert data["status"] == "PENDING"
    assert len(data["steps"]) == 1
    assert data["steps"][0]["tool_name"] == "tool.a"
    assert data["steps"][0]["arguments"] == {"b": 2}
