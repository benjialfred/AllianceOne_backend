from typing import Dict, Any, List
import json
from platform_services.alliance_ai.context.context_schema import AllianceAIContext
from platform_services.alliance_ai.tools.registry import ToolRegistry
from platform_services.alliance_ai.approvals.approval_engine import ApprovalEngine
from platform_services.alliance_ai.models.model_router import ModelRouter

class AgentOrchestrator:
    """
    The brain that ties context, tools, and the LLM together.
    Now acts as a Mission Control Orchestrator.
    """
    def __init__(self, model_router: ModelRouter):
        self.router = model_router

    def handle_request(self, prompt: str, context: AllianceAIContext, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Main execution loop for an AI request.
        """
        allowed_tools_schema = ToolRegistry.get_all_tools_schema(context)
        
        system_prompt = f"""Tu es Alliance AI, l'assistant intelligent et Chef de Mission de la plateforme ERP Alliance One.
Tu opères dans l'organisation : {context.organization_name}.
L'utilisateur actif est : {context.user_email}.
Module actif : {context.active_module or 'Aucun'}.

DIRECTIVE CRITIQUE :
Tu dois ABSOLUMENT répondre UNIQUEMENT au format JSON strict (sans aucun bloc markdown ```json). 
Si l'utilisateur pose une question simple, utilise le type "quick_answer". 
Si l'utilisateur demande une tâche complexe (ex: créer une boutique, un rapport financier), utilise le type "mission_plan" et définis 3 à 6 étapes concrètes.

Structure attendue :
{{
    "type": "quick_answer" | "mission_plan",
    "content": "Texte court et précis pour répondre à l'utilisateur.",
    "mission": {{
        "title": "Titre court de la mission (ex: Créer ma boutique)",
        "status": "PLANNING",
        "steps": [
            {{
                "id": "step_1",
                "title": "Titre de l'étape",
                "description": "Description courte",
                "type": "automatic" | "confirmation_required" | "input_required",
                "status": "pending"
            }}
        ]
    }}
}}

RÈGLES :
- N'invente pas de données. Utilise tes outils si nécessaire.
- Le champ "mission" est optionnel si type == "quick_answer".
- Le contenu ("content") doit être bref et direct.
"""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if history:
            messages.extend(history)
            
        messages.append({"role": "user", "content": prompt})

        provider = self.router.get_provider("default")
        response_text = provider.execute_tool_call_loop(messages, allowed_tools_schema, ToolRegistry, context)
        
        # Try to parse the LLM output as JSON
        try:
            parsed_response = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback if the LLM failed to output JSON
            parsed_response = {
                "type": "quick_answer",
                "content": response_text
            }
        
        return {
            "status": "SUCCESS",
            "content": parsed_response.get("content", ""),
            "data": parsed_response
        }
