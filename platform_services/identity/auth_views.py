from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from .models import User, Organization, OrganizationProfile, Membership
from .jwt_utils import decode_google_jwt


class SimpleLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            # Check if user has an organization profile with onboarding_completed
            onboarding_completed = False
            membership = Membership.objects.filter(user=user).select_related('organization').first()
            if membership:
                profile = OrganizationProfile.objects.filter(organization=membership.organization).first()
                if profile and profile.onboarding_completed:
                    onboarding_completed = True

            first_name = "Admin"
            last_name = "Alliance"
            if user.person:
                first_name = user.person.first_name
                last_name = user.person.last_name
            elif user.email:
                first_name = user.email.split('@')[0].capitalize()

            is_hyperadmin = False
            roles = ["ADMINISTRATOR"]
            if user.is_superuser or user.is_staff:
                is_hyperadmin = True
                roles = ["HYPERADMIN", "ADMINISTRATOR"]
            else:
                for m in Membership.objects.filter(user=user).select_related('role'):
                    if m.role.name.upper() == 'HYPERADMIN':
                        is_hyperadmin = True
                        roles = ["HYPERADMIN", "ADMINISTRATOR"]
                        break

            if is_hyperadmin:
                onboarding_completed = True

            return Response({
                "access": "dev-token-local",
                "refresh": "dev-refresh-local",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "roles": roles,
                    "is_hyperadmin": is_hyperadmin,
                    "permissions": ["*"],
                    "onboarding_completed": onboarding_completed,
                }
            })
        else:
            return Response({"detail": "Identifiants incorrects"}, status=401)


class GoogleAuthView(APIView):
    """
    Point de terminaison OAuth Google.
    POST /api/core/auth/google/
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        credential = request.data.get('credential')
        if not credential:
            return Response({"detail": "Token Google manquant"}, status=400)

        payload = decode_google_jwt(credential)
        if not payload or 'email' not in payload:
            return Response({"detail": "Token Google invalide"}, status=400)

        email = payload['email'].lower()
        first_name = (
            payload.get('given_name')
            or payload.get('name', '').split(' ')[0]
            or email.split('@')[0].capitalize()
        )
        last_name = payload.get('family_name') or 'Google'

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_active": True,
            }
        )

        # Vérifier si l'utilisateur possède déjà une organisation ayant complété l'onboarding
        onboarding_completed = False
        membership = Membership.objects.filter(user=user).select_related('organization').first()
        if membership:
            profile = OrganizationProfile.objects.filter(organization=membership.organization).first()
            if profile and profile.onboarding_completed:
                onboarding_completed = True

        return Response({
            "access": "google-session-access",
            "refresh": "google-session-refresh",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": first_name,
                "last_name": last_name,
                "roles": ["ADMINISTRATOR"],
                "permissions": ["*"],
                "onboarding_completed": onboarding_completed,
            }
        })


class RegisterView(APIView):
    """
    Création de compte classique.
    POST /api/core/auth/register/
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        if not email or not password:
            return Response({"detail": "Email et mot de passe requis"}, status=400)

        email = email.lower()
        if User.objects.filter(email=email).exists():
            return Response({"detail": "Un compte existe déjà avec cet email"}, status=400)

        user = User.objects.create(
            email=email,
            is_active=True
        )
        user.set_password(password)
        user.save()

        return Response({
            "access": "dev-token-register",
            "refresh": "dev-refresh-register",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": first_name or email.split('@')[0].capitalize(),
                "last_name": last_name or 'Alliance',
                "roles": ["ADMINISTRATOR"],
                "permissions": ["*"],
                "onboarding_completed": False,
            }
        })
