from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate

class SimpleLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            # We bypass actual JWT signing for now, just return a dummy token structure
            # so the frontend authStore works and allows the user in.
            return Response({
                "access": "dev-token-local",
                "refresh": "dev-refresh-local",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": "Admin",
                    "last_name": "Alliance",
                    "roles": ["ADMINISTRATOR"],
                    "permissions": ["*"]
                }
            })
        else:
            return Response({"detail": "Identifiants incorrects"}, status=401)
