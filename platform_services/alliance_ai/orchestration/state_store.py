from datetime import datetime, timezone
from typing import Optional
from platform_services.alliance_ai.models.orchestration import ExecutionPlanModel, ExecutionStepModel
from .state import ExecutionPlan, ExecutionStep, ExecutionStatus

class StateStore:
    """
    State Machine persistence engine (P1.6).
    Maps in-memory DAG representations to relational DB rows for long-running workflows.
    """

    @classmethod
    def save_plan(cls, plan: ExecutionPlan) -> None:
        """
        Persists the entire plan and its steps to the database.
        """
        plan_model, created = ExecutionPlanModel.objects.update_or_create(
            plan_id=plan.plan_id,
            defaults={
                "user_request": plan.user_request,
                "organization_id": plan.organization_id,
                "status": plan.status.value,
                "final_result": plan.final_result
            }
        )
        # If it was just created, overwrite created_at to match the plan's exact time
        if created and plan.created_at:
            plan_model.created_at = plan.created_at
            plan_model.save(update_fields=['created_at'])

        for step in plan.steps:
            ExecutionStepModel.objects.update_or_create(
                step_id=step.step_id,
                plan=plan_model,
                defaults={
                    "tool_name": step.tool_name,
                    "arguments": step.arguments,
                    "dependencies": step.dependencies,
                    "status": step.status.value,
                    "output": step.output,
                    "error": step.error,
                    "requires_confirmation": step.requires_confirmation,
                    "verification_status": step.verification_status,
                    "execution_metadata": step.execution_metadata
                }
            )

    @classmethod
    def load_plan(cls, plan_id: str) -> Optional[ExecutionPlan]:
        """
        Reconstructs the ExecutionPlan from the database.
        """
        try:
            plan_model = ExecutionPlanModel.objects.prefetch_related('steps').get(plan_id=plan_id)
        except ExecutionPlanModel.DoesNotExist:
            return None

        plan = ExecutionPlan(
            user_request=plan_model.user_request,
            organization_id=plan_model.organization_id,
            plan_id=plan_model.plan_id,
            created_at=plan_model.created_at,
            status=ExecutionStatus(plan_model.status),
            final_result=plan_model.final_result
        )

        for step_model in plan_model.steps.all():
            step = ExecutionStep(
                tool_name=step_model.tool_name,
                arguments=step_model.arguments,
                dependencies=step_model.dependencies,
                step_id=step_model.step_id,
                status=ExecutionStatus(step_model.status),
                output=step_model.output,
                error=step_model.error,
                requires_confirmation=step_model.requires_confirmation,
                verification_status=step_model.verification_status,
                execution_metadata=step_model.execution_metadata
            )
            plan.add_step(step)

        return plan
