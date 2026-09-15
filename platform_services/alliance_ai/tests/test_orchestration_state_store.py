import pytest
from django.utils import timezone
from platform_services.alliance_ai.orchestration.state import ExecutionPlan, ExecutionStep, ExecutionStatus
from platform_services.alliance_ai.orchestration.state_store import StateStore
from platform_services.alliance_ai.models.orchestration import ExecutionPlanModel, ExecutionStepModel

@pytest.mark.django_db
def test_save_and_load_plan():
    plan = ExecutionPlan(user_request="test request", organization_id="org1")
    plan.status = ExecutionStatus.WAITING_FOR_APPROVAL
    
    step1 = ExecutionStep(tool_name="tool.a", arguments={"arg1": 1}, step_id="step1")
    step1.status = ExecutionStatus.SUCCEEDED
    step1.output = {"data": "ok"}
    
    step2 = ExecutionStep(tool_name="tool.b", arguments={}, step_id="step2", dependencies=["step1"])
    step2.status = ExecutionStatus.WAITING_FOR_APPROVAL
    step2.requires_confirmation = True
    
    plan.add_step(step1)
    plan.add_step(step2)
    
    # Save
    StateStore.save_plan(plan)
    
    # Verify DB
    assert ExecutionPlanModel.objects.count() == 1
    assert ExecutionStepModel.objects.count() == 2
    
    # Load
    loaded_plan = StateStore.load_plan(plan.plan_id)
    
    assert loaded_plan is not None
    assert loaded_plan.plan_id == plan.plan_id
    assert loaded_plan.user_request == "test request"
    assert loaded_plan.organization_id == "org1"
    assert loaded_plan.status == ExecutionStatus.WAITING_FOR_APPROVAL
    
    assert len(loaded_plan.steps) == 2
    loaded_step1 = loaded_plan.get_step("step1")
    loaded_step2 = loaded_plan.get_step("step2")
    
    assert loaded_step1.status == ExecutionStatus.SUCCEEDED
    assert loaded_step1.output == {"data": "ok"}
    assert loaded_step1.tool_name == "tool.a"
    
    assert loaded_step2.status == ExecutionStatus.WAITING_FOR_APPROVAL
    assert loaded_step2.requires_confirmation is True
    assert loaded_step2.dependencies == ["step1"]

@pytest.mark.django_db
def test_load_non_existent_plan():
    loaded = StateStore.load_plan("does_not_exist")
    assert loaded is None
