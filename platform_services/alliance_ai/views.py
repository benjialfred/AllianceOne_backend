from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from platform_services.alliance_ai.gateway.gateway import AllianceAIGateway
from django.contrib.auth import get_user_model

class AskAllianceAIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        prompt = request.data.get('prompt')
        client_context = request.data.get('context', {})
        history = request.data.get('history', [])

        if not prompt:
            return Response({"error": "Prompt is required"}, status=400)

        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "Unauthorized. Authentication is required to use Alliance AI."}, status=401)

        # Delegate to the Gateway which handles isolation, RBAC and execution
        result = AllianceAIGateway.ask(
            user=user,
            prompt=prompt,
            client_context=client_context,
            history=history
        )

        return Response(result)

class MissionAuditView(APIView):
    """
    P1.8 Observability / Audit Trail
    Returns the complete execution trace for a given plan (mission).
    """
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
