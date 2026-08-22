from rest_framework.views import APIView
from rest_framework.response import Response
from platform_services.alliance_ai.gateway.gateway import AllianceAIGateway
from django.contrib.auth import get_user_model

class AskAllianceAIView(APIView):
    def post(self, request):
        prompt = request.data.get('prompt')
        client_context = request.data.get('context', {})
        history = request.data.get('history', [])

        if not prompt:
            return Response({"error": "Prompt is required"}, status=400)

        user = request.user
        if not user.is_authenticated:
            # Fallback for local development testing
            User = get_user_model()
            user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        # Delegate to the Gateway which handles isolation, RBAC and execution
        result = AllianceAIGateway.ask(
            user=user,
            prompt=prompt,
            client_context=client_context,
            history=history
        )

        return Response(result)
