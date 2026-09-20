from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from platform_services.alliance_ai.gateway.gateway import AllianceAIGateway
from platform_services.identity.authentication import AllianceTokenAuthentication
from django.contrib.auth import get_user_model

from platform_services.alliance_ai.models.conversation import AIConversationModel, AIMessageModel
from platform_services.alliance_ai.models.orchestration import ExecutionPlanModel

class AskAllianceAIView(APIView):
    authentication_classes = [AllianceTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        prompt = request.data.get('prompt')
        client_context = request.data.get('context', {})
        history = request.data.get('history', [])
        conversation_id = request.data.get('conversation_id')

        if not prompt:
            return Response({"error": "Prompt is required"}, status=400)

        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "Unauthorized. Authentication is required to use Alliance AI."}, status=401)

        # 1. Resolve or create persistent conversation session
        conversation = None
        if conversation_id:
            try:
                conversation = AIConversationModel.objects.filter(id=conversation_id, user=user).first()
            except Exception:
                conversation = None

        if not conversation:
            clean_title = prompt.strip().replace("\n", " ")
            if len(clean_title) > 50:
                clean_title = clean_title[:47] + "..."
            org_id = (
                client_context.get('organization_id') or 
                request.headers.get('X-Tenant-Id') or 
                request.headers.get('x-tenant-id') or 
                "default"
            )
            conversation = AIConversationModel.objects.create(
                user=user,
                organization_id=str(org_id),
                title=clean_title
            )
        elif conversation.title == "Nouvelle session" and conversation.messages.count() == 0:
            clean_title = prompt.strip().replace("\n", " ")
            if len(clean_title) > 50:
                clean_title = clean_title[:47] + "..."
            conversation.title = clean_title
            conversation.save(update_fields=['title'])

        # 2. Persist User Message
        user_msg = AIMessageModel.objects.create(
            conversation=conversation,
            sender=AIMessageModel.SENDER_USER,
            content=prompt,
            interaction_mode='DIRECT'
        )

        # 3. Pull recent conversation turns if history was not explicitly provided
        if not history and conversation.messages.count() > 1:
            prev_msgs = conversation.messages.exclude(id=user_msg.id).order_by('-created_at')[:8]
            history = [
                {"role": "user" if m.sender == AIMessageModel.SENDER_USER else "assistant", "content": m.content}
                for m in reversed(list(prev_msgs))
            ]

        # 4. Delegate to the Gateway which handles isolation, RBAC and execution
        result = AllianceAIGateway.ask(
            user=user,
            prompt=prompt,
            client_context=client_context,
            history=history
        )

        # 5. Persist Assistant Reply
        res_data = result.get('data', {})
        res_type = res_data.get('type')
        plan_id = result.get('plan_id')
        plan_model = ExecutionPlanModel.objects.filter(plan_id=plan_id).first() if plan_id else None

        interaction_mode = 'MISSION' if res_type == 'mission_plan' else 'DIRECT'
        content = result.get('content', '')

        assistant_msg = AIMessageModel.objects.create(
            conversation=conversation,
            sender=AIMessageModel.SENDER_ASSISTANT,
            content=content,
            interaction_mode=interaction_mode,
            mission=plan_model,
            metadata={"plan_id": plan_id} if plan_id else {}
        )

        # 6. Return response enriched with session and message identifiers
        result["conversation_id"] = str(conversation.id)
        result["conversation_title"] = conversation.title
        result["user_message_id"] = str(user_msg.id)
        result["message_id"] = str(assistant_msg.id)

        return Response(result)

class MissionAuditView(APIView):
    """
    P1.8 Observability / Audit Trail
    Returns the complete execution trace for a given plan (mission).
    """
    authentication_classes = [AllianceTokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request, plan_id):
        from platform_services.alliance_ai.models.orchestration import ExecutionPlanModel
        try:
            plan_model = ExecutionPlanModel.objects.prefetch_related('steps').get(plan_id=plan_id)
            
            steps = []
            for step in plan_model.steps.all():
                steps.append({
                    "step_id": step.step_id,
                    "tool_name": step.tool_name,
                    "status": step.status,
                    "arguments": step.arguments,
                    "output": step.output,
                    "error": step.error,
                    "verification_status": step.verification_status,
                    "execution_metadata": step.execution_metadata,
                    "dependencies": step.dependencies
                })
                
            return Response({
                "plan_id": plan_model.plan_id,
                "user_request": plan_model.user_request,
                "status": plan_model.status,
                "created_at": plan_model.created_at,
                "updated_at": plan_model.updated_at,
                "final_result": plan_model.final_result,
                "steps": steps
            })
        except ExecutionPlanModel.DoesNotExist:
            return Response({"error": "Plan not found"}, status=404)

class MissionConfirmView(APIView):
    """
    Submits user confirmation for a sensitive step.
    Revalidates the action hash against the Security Gate before execution.
    """
    authentication_classes = [AllianceTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        from platform_services.alliance_ai.orchestration.state_store import StateStore
        from platform_services.alliance_ai.gateway.gateway import _orchestrator
        from platform_services.alliance_ai.context.context_engine import ContextEngine

        step_id = request.data.get('step_id')
        if not step_id:
            return Response({"error": "step_id is required"}, status=400)

        plan = StateStore.load_plan(plan_id)
        if not plan:
            return Response({"error": "Plan not found"}, status=404)

        step = plan.get_step(step_id)
        if not step:
            return Response({"error": "Step not found"}, status=404)

        client_context = request.data.get('context', {})
        context = ContextEngine.build_context(request.user, client_context)

        action_hash = step.execution_metadata.get("action_hash")
        if not action_hash:
            from platform_services.alliance_ai.security.approval_engine import SecurityApprovalEngine
            approval = SecurityApprovalEngine.evaluate(
                tool_name=step.tool_name,
                arguments=step.arguments,
                context=context,
                mission_id=plan.plan_id
            )
            action_hash = approval.action_hash
            step.execution_metadata["action_hash"] = action_hash

        # Set confirmation hash for SecurityApprovalEngine to revalidate
        step.execution_metadata["confirmation_hash"] = action_hash
        step.requires_confirmation = False
        StateStore.save_plan(plan)

        # Resume plan through orchestrator
        _orchestrator.resume_plan(plan, context)

        return Response({"status": "SUCCESS", "message": f"Step {step_id} confirmed and plan resumed."})

class MissionCancelView(APIView):
    """
    Explicitly cancels an active mission.
    """
    authentication_classes = [AllianceTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        from platform_services.alliance_ai.orchestration.state_store import StateStore
        from platform_services.alliance_ai.orchestration.state import ExecutionStatus

        plan = StateStore.load_plan(plan_id)
        if not plan:
            return Response({"error": "Plan not found"}, status=404)

        plan.status = ExecutionStatus.CANCELLED
        for step in plan.steps:
            if step.status in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING, ExecutionStatus.WAITING_FOR_APPROVAL]:
                step.status = ExecutionStatus.CANCELLED

        StateStore.save_plan(plan)
        return Response({"status": "SUCCESS", "message": f"Mission {plan_id} has been cancelled."})
