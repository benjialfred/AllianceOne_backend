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
    """Uses LLM to build the plan."""
    def __init__(self):
        self.router = ModelRouter()

    def create_plan(self, user_request: str, context: AllianceAIContext) -> ExecutionPlan:
        # Get all allowed tools
        tools = ToolRegistry.get_all_tools_schema(context)
        tools_str = json.dumps(tools, indent=2, ensure_ascii=False)
        
        system_prompt = f"""Tu es Alliance AI, l'assistant intelligent et Chef de Mission.
Tu dois analyser la requête de l'utilisateur et générer un plan d'action (DAG).
Tu peux utiliser les outils suivants :
{tools_str}

DIRECTIVE CRITIQUE :
Réponds UNIQUEMENT avec un JSON strict contenant :
{{
    "content": "Message de notification immédiat (ex: 'Je m'occupe des stocks, des tâches et du scolaire, voici le plan !')",
    "steps": [
        {{
            "step_id": "step_1",
            "tool_name": "nom.de.l.outil",
            "arguments": {{"param": "value"}},
            "dependencies": [] // Liste des step_id précédents
        }}
    ]
}}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request}
        ]
        
        provider = self.router.get_provider("default")
        # Ask LLM to generate the JSON plan
        response_text = provider.generate(messages=messages)
        
        try:
            parsed = json.loads(response_text)
        except Exception:
            # Fallback
            parsed = {"content": "Plan généré par défaut", "steps": []}
            
        plan = ExecutionPlan(user_request=user_request, organization_id=context.organization_id)
        plan.user_request_response = parsed.get("content", "Exécution en cours...")
        
        for s in parsed.get("steps", []):
            original_step_id = s.get("step_id", str(uuid.uuid4()))
            unique_step_id = f"{plan.plan_id}_{original_step_id}"
            
            step = ExecutionStep(
                tool_name=s.get("tool_name"),
                arguments=s.get("arguments", {}),
                step_id=unique_step_id
            )
            # We also need to map the dependencies to use the new prefixed ids
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
    """
    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.planner = Planner()
        self.graph = DependencyGraph()
        self.executor = StepExecutor()
        self.verifier = VerificationEngine()

    def handle_request(self, user_request: str, context: AllianceAIContext) -> ExecutionPlan:
        """
        Main entry point for handling a new user request.
        """
        logger.info(f"Starting workflow for request: {user_request}")
        
        # 1. Analyze Intent
        intent = self.intent_analyzer.analyze(user_request)
        
        # 2. Planning
        plan = self.planner.create_plan(user_request, context)
        plan.status = ExecutionStatus.RUNNING
        StateStore.save_plan(plan)
        
        # 3. Execution Loop (Async Celery Task)
        from platform_services.alliance_ai.tasks import run_execution_loop_task
        context_dict = {
            "organization_id": context.organization_id,
            "user_id": context.user_id,
            "user_roles": context.user_roles,
            "session_id": context.session_id,
            "permissions": context.permissions,
            "active_module": context.active_module,
            "academic_year": context.academic_year
        }
        run_execution_loop_task.delay(plan.plan_id, context_dict)
        
        return plan

    def resume_plan(self, plan: ExecutionPlan, context: AllianceAIContext) -> ExecutionPlan:
        """
        Resumes a plan that was paused (e.g., WAITING_FOR_APPROVAL).
        """
        plan = StateStore.load_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")

        logger.info(f"Resuming plan: {plan.plan_id}")
        plan.status = ExecutionStatus.RUNNING
        self._run_execution_loop(plan, context)
        return plan

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
