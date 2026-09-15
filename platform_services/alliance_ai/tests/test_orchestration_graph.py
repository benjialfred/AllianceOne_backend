import pytest
from platform_services.alliance_ai.orchestration.state import ExecutionPlan, ExecutionStep, ExecutionStatus
from platform_services.alliance_ai.orchestration.graph import DependencyGraph

def test_executable_steps_without_dependencies():
    plan = ExecutionPlan("test", "org")
    s1 = ExecutionStep(tool_name="a", arguments={})
    s2 = ExecutionStep(tool_name="b", arguments={})
    plan.add_step(s1)
    plan.add_step(s2)
    
    graph = DependencyGraph()
    executable = graph.get_executable_steps(plan)
    
    assert len(executable) == 2
    assert s1 in executable
    assert s2 in executable

def test_executable_steps_with_dependencies():
    plan = ExecutionPlan("test", "org")
    s1 = ExecutionStep(tool_name="a", arguments={}, step_id="1")
    s2 = ExecutionStep(tool_name="b", arguments={}, step_id="2", dependencies=["1"])
    s3 = ExecutionStep(tool_name="c", arguments={}, step_id="3", dependencies=["1"])
    plan.add_step(s1)
    plan.add_step(s2)
    plan.add_step(s3)
    
    graph = DependencyGraph()
    
    # Initally only s1 is executable
    executable = graph.get_executable_steps(plan)
    assert len(executable) == 1
    assert executable[0].step_id == "1"
    
    # Mark s1 as succeeded
    s1.status = ExecutionStatus.SUCCEEDED
    executable = graph.get_executable_steps(plan)
    assert len(executable) == 2
    step_ids = {s.step_id for s in executable}
    assert "2" in step_ids
    assert "3" in step_ids

def test_failed_dependency_blocks_execution():
    plan = ExecutionPlan("test", "org")
    s1 = ExecutionStep(tool_name="a", arguments={}, step_id="1")
    s2 = ExecutionStep(tool_name="b", arguments={}, step_id="2", dependencies=["1"])
    plan.add_step(s1)
    plan.add_step(s2)
    
    graph = DependencyGraph()
    
    # Mark s1 as failed
    s1.status = ExecutionStatus.FAILED
    executable = graph.get_executable_steps(plan)
    # s2 cannot execute because s1 failed
    assert len(executable) == 0

def test_validate_graph_valid():
    plan = ExecutionPlan("test", "org")
    s1 = ExecutionStep(tool_name="a", arguments={}, step_id="1")
    s2 = ExecutionStep(tool_name="b", arguments={}, step_id="2", dependencies=["1"])
    plan.add_step(s1)
    plan.add_step(s2)
    
    graph = DependencyGraph()
    assert graph.validate_graph(plan) == True

def test_validate_graph_missing_dependency():
    plan = ExecutionPlan("test", "org")
    s1 = ExecutionStep(tool_name="a", arguments={}, step_id="1", dependencies=["999"])
    plan.add_step(s1)
    
    graph = DependencyGraph()
    assert graph.validate_graph(plan) == False

def test_validate_graph_circular_dependency():
    plan = ExecutionPlan("test", "org")
    s1 = ExecutionStep(tool_name="a", arguments={}, step_id="1", dependencies=["2"])
    s2 = ExecutionStep(tool_name="b", arguments={}, step_id="2", dependencies=["1"])
    plan.add_step(s1)
    plan.add_step(s2)
    
    graph = DependencyGraph()
    assert graph.validate_graph(plan) == False
