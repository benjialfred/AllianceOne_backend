import re
from typing import Any, Dict
from platform_services.alliance_ai.context.context_schema import AllianceAIContext
from platform_services.alliance_ai.tools.registry import ToolRegistry
from platform_services.alliance_ai.security.approval_engine import SecurityApprovalEngine
from platform_services.alliance_ai.security.types import Decision
from .state import ExecutionPlan, ExecutionStep, ExecutionStatus
import logging

logger = logging.getLogger(__name__)

class StepExecutor:
    """
    Executes a single step in the Execution Plan.
    Responsibilities (P1.4):
    - Resolve arguments from previous steps (Tool Chaining)
    - Enforce P0 Security Gate
    - Execute Tool
    - Catch errors safely
    """

    def __init__(self):
        # Regex to match {{step_id.output.key}} format
        self.template_regex = re.compile(r"\{\{([^}]+)\}\}")

    def execute(self, step: ExecutionStep, plan: ExecutionPlan, context: AllianceAIContext) -> ExecutionStep:
        logger.info(f"Executing step {step.step_id} - Tool: {step.tool_name}")
        
        from .state_store import StateStore
        step.status = ExecutionStatus.RUNNING
        StateStore.save_plan(plan)
        
        # 1. Resolve arguments (Tool Chaining)
        try:
            resolved_arguments = self._resolve_arguments(step.arguments, plan)
            step.execution_metadata["resolved_arguments"] = resolved_arguments
            
            # Idempotency Key (P1.7)
            idempotency_key = f"{plan.plan_id}-{step.step_id}"
            step.execution_metadata["idempotency_key"] = idempotency_key
            
        except Exception as e:
            self._fail_step(step, f"Argument resolution error: {str(e)}")
            return step

        # 2. P0 Security Gate
        try:
            provided_hash = step.execution_metadata.get("confirmation_hash")
            if provided_hash:
                approval = SecurityApprovalEngine.revalidate_confirmation(
                    tool_name=step.tool_name,
                    arguments=resolved_arguments,
                    context=context,
                    mission_id=plan.plan_id,
                    provided_hash=provided_hash
                )
            else:
                approval = SecurityApprovalEngine.evaluate(
                    tool_name=step.tool_name, 
                    arguments=resolved_arguments, 
                    context=context,
                    mission_id=plan.plan_id
                )
            
            if approval.decision == Decision.REQUIRE_CONFIRMATION:
                step.status = ExecutionStatus.WAITING_FOR_APPROVAL
                step.requires_confirmation = True
                step.execution_metadata["action_hash"] = approval.action_hash
                return step
                
            if approval.decision != Decision.ALLOW:
                self._fail_step(step, f"SECURITY_DENY: {approval.reason_code}")
                return step
                
        except Exception as e:
            self._fail_step(step, f"Security Gate error: {str(e)}")
            return step

        # 3. Execution
        try:
            # We can pass idempotency_key if ToolRegistry supports it, or just keep it in metadata
            output = ToolRegistry.execute_tool(step.tool_name, resolved_arguments, context)
            step.output = output
            step.status = ExecutionStatus.SUCCEEDED
            
        except Exception as e:
            self._fail_step(step, f"Tool execution failed: {str(e)}")
            
        return step

    def _fail_step(self, step: ExecutionStep, error_msg: str):
        step.status = ExecutionStatus.FAILED
        step.error = error_msg
        logger.error(f"Step {step.step_id} failed: {error_msg}")

    def _resolve_arguments(self, arguments: Dict[str, Any], plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Recursively resolves templated arguments.
        Example: {"invoice_id": "{{step_123.output.id}}"}
        """
        resolved = {}
        for key, value in arguments.items():
            if isinstance(value, str):
                resolved[key] = self._resolve_string(value, plan)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_arguments(value, plan)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_string(item, plan) if isinstance(item, str) else item 
                    for item in value
                ]
            else:
                resolved[key] = value
        return resolved

    def _resolve_string(self, value: str, plan: ExecutionPlan) -> Any:
        matches = self.template_regex.findall(value)
        if not matches:
            return value
            
        # If the string is EXACTLY the template, preserve type (e.g. integer or list)
        if len(matches) == 1 and f"{{{{{matches[0]}}}}}" == value:
            return self._get_value_from_plan(matches[0], plan)
            
        # If it's a mix like "The id is {{step_1.output.id}}", interpolate as string
        result = value
        for match in matches:
            val = self._get_value_from_plan(match, plan)
            result = result.replace(f"{{{{{match}}}}}", str(val))
        return result

    def _get_value_from_plan(self, path: str, plan: ExecutionPlan) -> Any:
        """
        Resolves a path like `step_123.output.data.0.id`
        """
        parts = path.split(".")
        if len(parts) < 2:
            raise ValueError(f"Invalid reference path: {path}")
            
        step_id = parts[0]
        field = parts[1] # usually "output"
        
        step = plan.get_step(step_id)
        if not step:
            raise ValueError(f"Referenced step {step_id} not found in plan")
            
        if step.status != ExecutionStatus.SUCCEEDED:
            raise ValueError(f"Cannot resolve reference from step {step_id} because it has not succeeded")
            
        current = getattr(step, field, None)
        
        # Traverse remaining parts (e.g., .data.0.id)
        for part in parts[2:]:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if idx < len(current):
                    current = current[idx]
                else:
                    current = None
            else:
                current = None
                
            if current is None:
                break
                
        return current
