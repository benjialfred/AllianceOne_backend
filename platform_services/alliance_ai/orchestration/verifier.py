import logging
from typing import Any, Dict
from platform_services.alliance_ai.context.context_schema import AllianceAIContext
from platform_services.alliance_ai.tools.registry import ToolRegistry
from .state import ExecutionStep

logger = logging.getLogger(__name__)

class VerificationEngine:
    """
    Verification Engine (P1.5)
    Ensures that a successful tool execution actually produced valid business results.
    Prevents the orchestrator from continuing if a step silently failed.
    """

    def verify(self, step: ExecutionStep, context: AllianceAIContext) -> bool:
        logger.info(f"Verifying output for step {step.step_id} (Tool: {step.tool_name})")
        
        output = step.output
        
        # 1. Baseline Heuristics Check (Common error patterns)
        if isinstance(output, dict):
            if "error" in output or output.get("status") == "error":
                error_msg = output.get("error") or output.get("message") or "Unknown error"
                self._fail_verification(step, f"Logical error detected in output: {error_msg}")
                return False

        # 2. Tool-Specific Verification (if defined in the tool)
        # We look up the tool to see if it provides a custom verification method
        try:
            tool_def = ToolRegistry.get_tool(step.tool_name)
            if hasattr(tool_def, "verify_output") and callable(tool_def.verify_output):
                is_valid, reason = tool_def.verify_output(step.arguments, output, context)
                if not is_valid:
                    self._fail_verification(step, f"Tool verification failed: {reason}")
                    return False
        except Exception as e:
            # If tool doesn't exist or verify_output crashes, we fail the verification
            self._fail_verification(step, f"Verification process crashed: {str(e)}")
            return False

        # 3. Data expectation check based on tool intent
        # For instance, if tool name implies "search" or "get", and output is suspiciously empty.
        if "search" in step.tool_name or "get" in step.tool_name:
            if output is None or (isinstance(output, list) and len(output) == 0):
                # We don't necessarily fail a search that yields 0 results, 
                # but we note it in metadata. For strict workflows, this could be a failure.
                step.execution_metadata["verification_note"] = "Empty result set returned."

        self._pass_verification(step)
        return True

    def _fail_verification(self, step: ExecutionStep, reason: str):
        step.verification_status = f"FAILED: {reason}"
        logger.warning(f"Verification failed for step {step.step_id}: {reason}")

    def _pass_verification(self, step: ExecutionStep):
        step.verification_status = "VERIFIED"
        logger.info(f"Step {step.step_id} verified successfully.")
