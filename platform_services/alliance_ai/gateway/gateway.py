from typing import Dict, Any, List
from django.contrib.auth import get_user_model
from platform_services.alliance_ai.context.context_engine import ContextEngine
from platform_services.alliance_ai.orchestration.orchestrator import AllianceAIOrchestrator

User = get_user_model()

# Global Instances for the OS
_orchestrator = AllianceAIOrchestrator()

class AllianceAIGateway:
    """
    The SINGLE entry point for all Bounded Contexts and API endpoints to access Alliance AI.
    """

    @classmethod
    def ask(cls, user: User, prompt: str, client_context: Dict[str, Any], history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Processes a conversational AI request.
        """
        # 1. Resolve highly secure context
        ai_context = ContextEngine.build_context(user, client_context)
        
        # 2. Hand off to Orchestrator (Returns ExecutionPlan)
        try:
            plan = _orchestrator.handle_request(prompt, ai_context)
            return {
                "status": "SUCCESS",
                "plan_id": plan.plan_id,
                "content": getattr(plan, "user_request_response", "Je traite votre demande..."),
                "data": {
                    "type": "mission_plan",
                    "mission": {
                        "title": "Mission en cours",
                        "status": plan.status.value,
                        "steps": []
                    }
                }
            }
        except Exception as e:
            # Audit the error
            import traceback
            traceback.print_exc()
            return {
                "status": "ERROR",
                "content": "Je suis désolé, une erreur interne m'empêche de traiter votre demande.",
                "details": str(e)
            }
