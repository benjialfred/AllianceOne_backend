from celery import shared_task
import logging
from platform_services.alliance_ai.orchestration.state_store import StateStore
from platform_services.alliance_ai.orchestration.state import ExecutionStatus
from platform_services.alliance_ai.context.context_schema import AllianceAIContext
import json

logger = logging.getLogger(__name__)

@shared_task
def run_execution_loop_task(plan_id: str, context_dict: dict):
    """
    Celery task that runs the AI Orchestrator Execution Loop in the background.
    """
    logger.info(f"Starting Celery background execution for plan {plan_id}")
    
    # We reconstruct the context from the dictionary
    context = AllianceAIContext(**context_dict)
    
    # Re-import orchestrator inside to avoid circular dependency
    from platform_services.alliance_ai.orchestration.orchestrator import AllianceAIOrchestrator
    
    plan = StateStore.load_plan(plan_id)
    if not plan:
        logger.error(f"Plan {plan_id} not found.")
        return
        
    orchestrator = AllianceAIOrchestrator()
    orchestrator._run_execution_loop(plan, context)
