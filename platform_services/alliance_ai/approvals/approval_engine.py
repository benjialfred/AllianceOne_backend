from typing import Dict, Any, Tuple
from platform_services.alliance_ai.tools.definitions import RiskLevel, AIToolDefinition
from platform_services.alliance_ai.context.context_schema import AllianceAIContext

class ApprovalEngine:
    """
    Evaluates if an AI requested action requires human confirmation.
    """
    
    @classmethod
    def evaluate_risk(cls, tool: AIToolDefinition, context: AllianceAIContext, args: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Returns (requires_approval, reason)
        """
        # 1. Explicit override
        if tool.requires_confirmation:
            return True, "Outil sensible requérant toujours une confirmation."
            
        # 2. Level evaluation
        if tool.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return True, f"Niveau de risque {tool.risk_level.value} détecté."
            
        # 3. Superuser leniency (optional business logic)
        # If we wanted admins to bypass MEDIUM risks, we'd do it here.
        # For now, LOW and MEDIUM pass through automatically.
        
        return False, "Exécution sûre."

    @classmethod
    def request_approval(cls, tool: AIToolDefinition, context: AllianceAIContext, args: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """
        Prepares the payload that the Orchestrator will send back to the frontend 
        to trigger the UI Approval dialog.
        """
        return {
            "status": "APPROVAL_REQUIRED",
            "reason": reason,
            "action_details": {
                "tool": tool.name,
                "description": tool.description,
                "args": args
            }
        }
