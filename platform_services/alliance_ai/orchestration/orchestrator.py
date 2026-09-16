import logging
from typing import Dict, Any, List, Optional
from platform_services.alliance_ai.context.context_schema import AllianceAIContext
from .state import ExecutionPlan, ExecutionStep, ExecutionStatus

logger = logging.getLogger(__name__)

import json
import uuid
import threading
from platform_services.alliance_ai.models.model_router import ModelRouter
from platform_services.alliance_ai.tools.registry import ToolRegistry
from .state_store import StateStore

class IntentAnalyzer:
    """Stub for Intent Analysis (to be fully implemented)"""
    def analyze(self, user_request: str) -> Dict[str, Any]:
        return {"intent": "mission"}

class Planner:
    """Uses LLM to build the plan or provide instant conversational answers."""
    def __init__(self):
        self.router = ModelRouter()

    def create_plan(self, user_request: str, context: AllianceAIContext, history: List[Dict[str, str]] = None) -> ExecutionPlan:
        # Get all allowed tools
        tools = ToolRegistry.get_all_tools_schema(context)
        tools_str = json.dumps(tools, indent=2, ensure_ascii=False)
        
        system_prompt = f"""Tu es Alliance AI, l'assistant intelligent et chef d'orchestre d'Alliance One (ERP scolaire et de gestion d'entreprise).
Tu disposes des outils système suivants pour interagir avec la plateforme :
{tools_str}

DIRECTIVE CRITIQUE D'AIGUILLAGE :
1. TYPE "chat" (Questions simples, salutations, explications, conseils d'utilisation) :
- Si la demande de l'utilisateur est une salutation, une question générale, une demande d'information, un renseignement ou une assistance qui NE NÉCESSITE PAS d'exécuter d'outils système :
- Réponds DIRECTEMENT, de manière complète, chaleureuse et structurée dans "content".
- Ne génère AUCUN outil. Le tableau "steps" DOIT être vide [].
- "type" DOIT être "chat".

2. TYPE "mission_plan" (Tâches, actions système, modifications, créations de données) :
- Si la demande exige d'effectuer une action concrète nécessitant un ou plusieurs outils système listés ci-dessus (ex: inscrire un élève, émettre une facture, enregistrer un paiement, créer une tâche, ajuster un stock) :
- Donne un court message d'annonce dans "content" (ex: "J'enregistre le nouvel élève dans la classe demandée...").
- Décris les étapes d'exécution dans le tableau "steps" avec "tool_name", "arguments", et "dependencies".
- "type" DOIT être "mission_plan".

FORMAT DE SORTIE STRICT (JSON UNIQUEMENT) :
{{
    "type": "chat" ou "mission_plan",
    "content": "Votre réponse directe ou votre annonce de mission",
    "steps": [
        {{
            "step_id": "step_1",
            "tool_name": "nom.de.l.outil",
            "arguments": {{"param": "value"}},
            "dependencies": []
        }}
    ]
}}
"""
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for h in history[-5:]:
                if h.get("role") in ["user", "assistant"] and h.get("content"):
                    messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_request})
        
        provider = self.router.get_provider("default")
        # Ask LLM to generate the JSON plan or answer
        response_text = provider.generate(messages=messages)
        
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        try:
            parsed = json.loads(cleaned_text)
        except Exception:
            # Fallback to direct conversational response
            parsed = {"type": "chat", "content": response_text, "steps": []}
            
        plan = ExecutionPlan(user_request=user_request, organization_id=context.organization_id)
        plan_type = parsed.get("type", "chat" if not parsed.get("steps") else "mission_plan")
        plan.plan_type = plan_type
        plan.user_request_response = parsed.get("content", "Je traite votre demande...")
        
        for s in parsed.get("steps", []):
            original_step_id = s.get("step_id", str(uuid.uuid4()))
            unique_step_id = f"{plan.plan_id}_{original_step_id}"
            
            step = ExecutionStep(
                tool_name=s.get("tool_name"),
                arguments=s.get("arguments", {}),
                step_id=unique_step_id
            )
            step.dependencies = [f"{plan.plan_id}_{dep}" for dep in s.get("dependencies", [])]
            plan.add_step(step)
            
        return plan

from .graph import DependencyGraph

from .executor import StepExecutor

from .verifier import VerificationEngine

class AllianceAIOrchestrator:
    """
    Central orchestration engine for Alliance AI (P1).
    Replaces the naive LLM loop with a verifiable, traceable Execution Graph.
    Fast-tracks simple questions to return immediate answers without delays.
    """
    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.planner = Planner()
        self.graph = DependencyGraph()
        self.executor = StepExecutor()
        self.verifier = VerificationEngine()

    def handle_request(self, user_request: str, context: AllianceAIContext, history: List[Dict[str, str]] = None) -> ExecutionPlan:
        """
        Main entry point for handling a user request.
        Fast-tracks simple questions immediately without running background workers.
        """
        logger.info(f"Starting workflow for request: {user_request}")
        
        # 1. Planning
        plan = self.planner.create_plan(user_request, context, history=history)
        
        # 2. FAST-TRACK : Simple Q&A / Chat without tools
        if len(plan.steps) == 0 or plan.plan_type == "chat":
            plan.status = ExecutionStatus.SUCCEEDED
            plan.plan_type = "chat"
            StateStore.save_plan(plan)
            return plan

        # 3. MISSION / TOOLS : Actual background execution
        plan.status = ExecutionStatus.RUNNING
        plan.plan_type = "mission_plan"
        StateStore.save_plan(plan)
        
        context_dict = context.to_dict()
        try:
            from platform_services.alliance_ai.tasks import run_execution_loop_task
            run_execution_loop_task.delay(plan.plan_id, context_dict)
        except Exception as e:
            logger.warning(f"Celery task dispatch failed or offline ({e}), falling back to direct execution")
            self._run_execution_loop(plan, context)
            
        return plan

    def resume_plan(self, plan: ExecutionPlan, context: AllianceAIContext) -> ExecutionPlan:
        """
        Resumes a plan that was paused (e.g., WAITING_FOR_APPROVAL).
        """
        if isinstance(plan, ExecutionPlan):
            loaded_plan = plan
        else:
            loaded_plan = StateStore.load_plan(str(plan))
            if not loaded_plan:
                raise ValueError(f"Plan {plan} not found.")

        logger.info(f"Resuming plan: {loaded_plan.plan_id}")
        loaded_plan.status = ExecutionStatus.RUNNING
        StateStore.save_plan(loaded_plan)
        self._run_execution_loop(loaded_plan, context)
        return loaded_plan

    def _run_execution_loop(self, plan: ExecutionPlan, context: AllianceAIContext):
        """
        Executes the plan using the Dependency Graph until completion, failure, or pause.
        """
        while True:
            # Get steps that are ready to run
            ready_steps = self.graph.get_executable_steps(plan)
            
            if not ready_steps:
                # No more steps to run. Are we done or stuck?
                pending = plan.get_steps_by_status(ExecutionStatus.PENDING)
                waiting_approval = plan.get_steps_by_status(ExecutionStatus.WAITING_FOR_APPROVAL)
                
                if waiting_approval:
                    plan.status = ExecutionStatus.WAITING_FOR_APPROVAL
                elif pending:
                    # We have pending steps but they aren't executable -> BLOCKED by dependencies
                    plan.status = ExecutionStatus.BLOCKED
                else:
                    # All steps completed
                    plan.status = ExecutionStatus.SUCCEEDED
                
                StateStore.save_plan(plan)
                break

            for step in ready_steps:
                step.status = ExecutionStatus.RUNNING
                
                # Execute step (this will invoke SecurityGate in P1.4)
                self.executor.execute(step, plan, context)
                
                if step.status == ExecutionStatus.SUCCEEDED:
                    # Verify
                    is_verified = self.verifier.verify(step, context)
                    if not is_verified:
                        step.status = ExecutionStatus.VERIFICATION_FAILED
                        plan.status = ExecutionStatus.FAILED
                        StateStore.save_plan(plan)
                        return # Abort plan on verification failure
                elif step.status == ExecutionStatus.WAITING_FOR_APPROVAL:
                    # Pause the entire plan
                    plan.status = ExecutionStatus.WAITING_FOR_APPROVAL
                    StateStore.save_plan(plan)
                    return
                elif step.status == ExecutionStatus.FAILED:
                    plan.status = ExecutionStatus.FAILED
                    StateStore.save_plan(plan)
                    return # Abort plan on failure
            
            StateStore.save_plan(plan)
                    
        # Update plan final status
        if plan.status == ExecutionStatus.RUNNING:
            plan.status = ExecutionStatus.SUCCEEDED
            StateStore.save_plan(plan)
