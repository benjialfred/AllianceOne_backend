from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from platform_services.identity.models import Organization, Workspace, User, Person, Role, OrganizationProfile
from platform_services.identity.mixins import TenantQuerySetMixin
from .serializers import (
    OrganizationSerializer, WorkspaceSerializer, UserSerializer,
    PersonSerializer, RoleSerializer, OnboardingSubmitSerializer,
    OrganizationProfileSerializer,
)

@api_view(['GET'])
def get_available_modules(request):
    """
    Retourne la liste des modules (manifestes) autorisés pour le tenant actuel.
    Pour l'instant, on simule que le module Education est activé.
    """
    # Ici, nous lirions les licences ou permissions de l'Organisation
    tenant_id = request.headers.get('X-Tenant-ID')
    if not tenant_id:
        return Response({'detail': 'Tenant ID missing'}, status=400)
    
    modules = [
        {
            'id': 'education',
            'name': 'Education',
            'version': '1.0.0',
            'description': 'Gestion de scolarité',
            'routes': [{'path': '/students', 'component': 'pages/Students'}],
            'commands': [
                {
                    'id': 'new_student',
                    'title': 'Nouveau dossier Étudiant',
                    'shortcut': ['⌘', 'N'],
                    'action_event': 'Education:OpenNewStudentModal',
                }
            ],
            'events': {'emits': [], 'listens': ['Education:OpenNewStudentModal']}
        },
        {
            'id': 'library',
            'name': 'Bibliothèque',
            'version': '1.0.0',
            'description': 'Gestion des prêts et du catalogue',
            'routes': [],
            'commands': [],
            'events': {'emits': [], 'listens': []}
        }
    ]
    return Response(modules)


@api_view(['GET'])
def onboarding_status(request):
    """
    Vérifie si l'organisation a complété l'onboarding.
    GET /api/core/identity/onboarding/status/
    """
    tenant_id = request.headers.get('X-Tenant-ID')
    org = None
    if tenant_id:
        org = Organization.objects.filter(id=tenant_id).first()
    
    if not org and request.user and request.user.is_authenticated:
        membership = getattr(request.user, 'memberships', None)
        if membership:
            m = membership.select_related('organization').first()
            if m:
                org = m.organization

    if not org:
        org = Organization.objects.first()

    if org:
        profile = OrganizationProfile.objects.filter(organization=org).first()
        if profile and profile.onboarding_completed:
            return Response({
                'onboarding_completed': True,
                'organization_id': str(org.id),
                'organization_name': org.name,
                'profile': OrganizationProfileSerializer(profile).data,
            })
    return Response({'onboarding_completed': False})


@api_view(['POST'])
def onboarding_submit(request):
    """
    Soumet les données du wizard d'onboarding.
    POST /api/core/identity/onboarding/
    Crée ou met à jour l'OrganizationProfile et marque l'onboarding comme complété.
    """
    serializer = OnboardingSubmitSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    tenant_id = request.headers.get('X-Tenant-ID')
    org = None
    if tenant_id:
        org = Organization.objects.filter(id=tenant_id).first()
    
    if not org and request.user and request.user.is_authenticated:
        m = getattr(request.user, 'memberships', None)
        if m:
            first_m = m.first()
            if first_m:
                org = first_m.organization

    if not org:
        org = Organization.objects.first()

    if not org:
        org = Organization.objects.create(
            name=data['organization_name'],
            legal_name=data.get('legal_name', ''),
            registration_number=data.get('registration_number', ''),
        )
    else:
        org.name = data['organization_name']
        if data.get('legal_name'):
            org.legal_name = data['legal_name']
        if data.get('registration_number'):
            org.registration_number = data['registration_number']
        org.active_modules = data['selected_modules']
        org.save()

    # Si l'utilisateur est connecté, s'assurer qu'il a une membership
    if request.user and request.user.is_authenticated:
        role, _ = Role.objects.get_or_create(
            organization=org,
            name="Administrateur",
            defaults={"description": "Super Administrateur de l'organisation"}
        )
        Membership.objects.get_or_create(user=request.user, organization=org, defaults={"role": role})
    
    # Créer ou mettre à jour le profil avec onboarding_completed = True
    profile, created = OrganizationProfile.objects.update_or_create(
        organization=org,
        defaults={
            'sector': data.get('sector', ''),
            'sub_sector': data.get('sub_sector', ''),
            'country': data.get('country', 'CM'),
            'city': data.get('city', ''),
            'employee_count': data.get('employee_count', ''),
            'phone': data.get('phone', ''),
            'website': data.get('website', ''),
            'selected_modules': data['selected_modules'],
            'onboarding_completed': True,
            'onboarding_completed_at': timezone.now(),
        }
    )
    
    return Response({
        'status': 'ok',
        'organization_id': str(org.id),
        'organization_name': org.name,
        'onboarding_completed': True,
        'profile': OrganizationProfileSerializer(profile).data,
    }, status=status.HTTP_200_OK)


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Gestion globale des organisations. (Généralement réservée au SuperAdmin).
    Ici, nous n'appliquons pas le TenantQuerySetMixin car l'Organization n'a pas d'organisation parente.
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class WorkspaceViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """
    Espaces de travail isolés par Tenant.
    """
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    Utilisateurs globaux de la plateforme.
    Dans une vraie implémentation, on filtrerait via la table de liaison Membership.
    Pour l'instant, accès global avec AllowAny.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer


class PersonViewSet(viewsets.ModelViewSet):
    """
    Gestion des entités Person.
    """
    queryset = Person.objects.all()
    serializer_class = PersonSerializer


class RoleViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """
    Gestion des rôles RBAC (isolés par Tenant).
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
