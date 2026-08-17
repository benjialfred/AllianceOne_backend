from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from platform_services.identity.models import Organization, Workspace, User, Person, Role
from platform_services.identity.mixins import TenantQuerySetMixin
from .serializers import OrganizationSerializer, WorkspaceSerializer, UserSerializer, PersonSerializer, RoleSerializer

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
