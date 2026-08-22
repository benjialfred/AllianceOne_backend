from typing import Dict, Any, List
from platform_services.alliance_ai.context.context_schema import AllianceAIContext
from platform_services.alliance_ai.tools.registry import ToolRegistry
from platform_services.alliance_ai.approvals.approval_engine import ApprovalEngine
from platform_services.alliance_ai.models.model_router import ModelRouter

class AgentOrchestrator:
    """
    The brain that ties context, tools, and the LLM together.
    """
    def __init__(self, model_router: ModelRouter):
        self.router = model_router

    def handle_request(self, prompt: str, context: AllianceAIContext, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Main execution loop for an AI request.
        """
        # 1. Fetch allowed tools for this specific context
        allowed_tools_schema = ToolRegistry.get_all_tools_schema(context)
        
        # 2. Prepare the system prompt with context
        system_prompt = f"""
        Tu es Alliance AI.
        Tu opères dans l'organisation : {context.organization_name}.
        L'utilisateur actif est : {context.user_email}.
        Module actif : {context.active_module or 'Aucun'}.
        Route : {context.active_route or 'Aucune'}.
        Année : {context.academic_year or 'Non spécifiée'}.
        
        Utilise EXCLUSIVEMENT les outils fournis pour obtenir des données. 
        Ne fabrique jamais de données.
        """
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        if history:
            messages.extend(history)
            
        messages.append({"role": "user", "content": prompt})

        # 3. Select Model Provider
        provider = self.router.get_provider("default")

        # 4. In a real implementation, we pass allowed_tools_schema to the provider
        # and enter a Tool-Call loop.
        # If the LLM decides to call a tool, the Orchestrator intercepts it here,
        # checks ApprovalEngine.evaluate_risk(), and if safe, calls ToolRegistry.execute_tool().
        
        # For the V1 Backend Mock, we'll simulate a successful loop:
        response_text = provider.execute_tool_call_loop(messages, allowed_tools_schema, ToolRegistry, context)
        
        # 5. Log the interaction to the EventBus (Audit)
        # EventBus.publish(AIInteractionEvent(...))
        
        return {
            "status": "SUCCESS",
            "content": response_text
        }
