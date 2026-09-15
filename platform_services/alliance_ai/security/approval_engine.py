from typing import Dict, Any, Optional
import logging

from platform_services.alliance_ai.context.context_schema import AllianceAIContext
from platform_services.alliance_ai.tools.registry import ToolRegistry
from platform_services.alliance_ai.tools.definitions import RiskLevel
from .types import Decision, ApprovalDecision, generate_canonical_action_hash
from .permission_resolver import PermissionResolver
from .policy_engine import PolicyEngine
from .exceptions import SecurityGateError

logger = logging.getLogger(__name__)

class SecurityApprovalEngine:
    """
    The final authority for all AI tool executions.
    Evaluates identity, permissions, tenant isolation, and risk.
    """

    @classmethod
    def evaluate(cls, tool_name: str, arguments: Dict[str, Any], context: AllianceAIContext, mission_id: str = "default") -> ApprovalDecision:
        """
        Main security gate following the 14-step validation requirement.
        """
        user_id = context.user_id
        organization_id = context.organization_id

        # 1 & 2 & 3. Authentication and Identity Context
        if not user_id or not organization_id:
            return cls._deny(tool_name, "UNAUTHENTICATED", "Missing user or organization context.")

        membership = PermissionResolver.resolve_membership(user_id, organization_id)
        if not membership:
            return cls._deny(tool_name, "MEMBERSHIP_NOT_FOUND", "User is not a member of the active organization.")

        # 6. Resolve tool policy (Also protects against invented tools)
        try:
            tool_policy = ToolRegistry.get_tool(tool_name)
        except ValueError:
            return cls._deny(tool_name, "UNKNOWN_TOOL", "Tool does not exist in registry.")

        # 5. Resolve & Evaluate Permissions
        if not PolicyEngine.evaluate_permissions(user_id, organization_id, tool_policy.required_permissions):
            return cls._deny(tool_name, "PERMISSION_DENIED", "User lacks required RBAC permissions.")

        # 8 & 9. Validate tenant scope & Object ownership (Argument level isolation)
        if not PolicyEngine.validate_object_ownership(tool_policy.object_scope, arguments, organization_id):
            return cls._deny(tool_name, "TENANT_MISMATCH", "Arguments violate tenant isolation bounds.")

        # 11 & 12. Determine risk and confirmation requirement
        requires_confirmation = False
        if tool_policy.requires_confirmation or tool_policy.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            requires_confirmation = True

        # 13. Generate Action Hash (even if not confirming, useful for audit)
        action_hash = generate_canonical_action_hash(
            mission_id=mission_id,
            organization_id=organization_id,
            user_id=user_id,
            tool_name=tool_name,
            arguments=arguments
        )

        decision = Decision.REQUIRE_CONFIRMATION if requires_confirmation else Decision.ALLOW

        result = ApprovalDecision(
            decision=decision,
            requires_confirmation=requires_confirmation,
            reason="Execution authorized." if decision == Decision.ALLOW else "Action requires explicit user confirmation.",
            risk_level=tool_policy.risk_level.value,
            policy=str(tool_policy.required_permissions),
            user_id=user_id,
            organization_id=organization_id,
            tool=tool_name,
            action_hash=action_hash,
            reason_code="AUTHORIZED" if decision == Decision.ALLOW else "CONFIRMATION_REQUIRED"
        )
        
        cls._audit_log(result)
        return result

    @classmethod
    def revalidate_confirmation(cls, tool_name: str, arguments: Dict[str, Any], context: AllianceAIContext, mission_id: str, provided_hash: str) -> ApprovalDecision:
        """
        Step 8 from Requirements: Revalidation at execution time.
        Called when frontend submits a confirmation.
        """
        # Complete full revalidation to ensure permissions or state didn't change
        decision = cls.evaluate(tool_name, arguments, context, mission_id)
        
        if decision.decision == Decision.DENY:
            # If it became DENY since confirmation (e.g., lost permission)
            return decision
            
        # Verify hash matches exactly to ensure arguments weren't tampered with
        if decision.action_hash != provided_hash:
            return cls._deny(tool_name, "ACTION_HASH_MISMATCH", "Arguments have been altered since confirmation.")
            
        # If it passes, we override to ALLOW (since the user provided the valid confirmation)
        decision.decision = Decision.ALLOW
        decision.reason_code = "CONFIRMATION_VALIDATED"
        decision.reason = "Hash and permissions revalidated successfully."
        decision.requires_confirmation = False
        
        cls._audit_log(decision)
        return decision

    @classmethod
    def _deny(cls, tool_name: str, reason_code: str, reason: str) -> ApprovalDecision:
        result = ApprovalDecision(
            decision=Decision.DENY,
            requires_confirmation=False,
            reason=reason,
            risk_level="UNKNOWN",
            policy="UNKNOWN",
            user_id=None,
            organization_id=None,
            tool=tool_name,
            reason_code=reason_code
        )
        cls._audit_log(result)
        return result

    @classmethod
    def _audit_log(cls, decision: ApprovalDecision):
        """
        Secure Audit Logging (Point 17 & 20).
        """
        # In a real app, this goes to ELK / CloudWatch / DB Audit Log
        logger.info(f"SECURITY_AUDIT: Tool={decision.tool} Decision={decision.decision.value} Reason={decision.reason_code}")
