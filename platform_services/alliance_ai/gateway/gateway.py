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
            plan = _orchestrator.handle_request(prompt, ai_context, history=history)
            
            # Fast-track for simple questions / direct chat (no tools needed)
            if getattr(plan, "plan_type", "mission_plan") == "chat" or len(plan.steps) == 0:
                content = getattr(plan, "user_request_response", "Voici ma réponse.")
                return {
                    "status": "SUCCESS",
                    "plan_id": plan.plan_id,
                    "content": content,
                    "data": {
                        "type": "chat",
                        "content": content
                    }
                }
            
            # Mission requiring tool execution
            return {
                "status": "SUCCESS",
                "plan_id": plan.plan_id,
                "content": getattr(plan, "user_request_response", "Je prépare l'exécution des tâches..."),
                "data": {
                    "type": "mission_plan",
                    "mission": {
                        "title": getattr(plan, "title", "Mission en cours"),
                        "status": plan.status.value,
                        "steps": [s.to_dict() for s in plan.steps]
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
