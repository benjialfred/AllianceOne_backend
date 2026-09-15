import pytest
from platform_services.alliance_ai.orchestration.state import ExecutionStep
from platform_services.alliance_ai.orchestration.verifier import VerificationEngine
from platform_services.alliance_ai.context.context_schema import AllianceAIContext
from unittest.mock import patch, MagicMock

def get_context():
    return AllianceAIContext(user_id="u1", user_email="a@a.com", organization_id="org1", organization_name="Org1")

@patch("platform_services.alliance_ai.orchestration.verifier.ToolRegistry.get_tool")
def test_verify_success(mock_get_tool):
    mock_get_tool.return_value = MagicMock()
    engine = VerificationEngine()
    step = ExecutionStep(tool_name="test.tool", arguments={})
    step.output = {"success": True, "data": [1, 2]}
    
    assert engine.verify(step, get_context()) == True
    assert step.verification_status == "VERIFIED"

def test_verify_detects_error_key():
    engine = VerificationEngine()
    step = ExecutionStep(tool_name="test.tool", arguments={})
    step.output = {"error": "Invalid input"}
    
    assert engine.verify(step, get_context()) == False
    assert "FAILED: Logical error detected" in step.verification_status
    assert "Invalid input" in step.verification_status

def test_verify_detects_error_status():
    engine = VerificationEngine()
    step = ExecutionStep(tool_name="test.tool", arguments={})
    step.output = {"status": "error", "message": "Something went wrong"}
    
    assert engine.verify(step, get_context()) == False
    assert "FAILED: Logical error detected" in step.verification_status
    assert "Something went wrong" in step.verification_status

@patch("platform_services.alliance_ai.orchestration.verifier.ToolRegistry.get_tool")
def test_verify_tool_specific_logic(mock_get_tool):
    engine = VerificationEngine()
    step = ExecutionStep(tool_name="custom.tool", arguments={})
    step.output = {"result": 42}
    
    # Mock a tool definition with custom verify_output
    mock_tool = MagicMock()
    # verify_output returns (is_valid, reason)
    mock_tool.verify_output.return_value = (False, "Business logic failed")
    mock_get_tool.return_value = mock_tool
    
    assert engine.verify(step, get_context()) == False
    assert "Tool verification failed: Business logic failed" in step.verification_status
    mock_tool.verify_output.assert_called_once_with({}, {"result": 42}, get_context())

@patch("platform_services.alliance_ai.orchestration.verifier.ToolRegistry.get_tool")
def test_verify_search_empty_result(mock_get_tool):
    mock_get_tool.return_value = MagicMock()
    engine = VerificationEngine()
    step = ExecutionStep(tool_name="search.users", arguments={})
    step.output = []
    
    # Doesn't fail, but adds a note
    assert engine.verify(step, get_context()) == True
    assert step.execution_metadata["verification_note"] == "Empty result set returned."
