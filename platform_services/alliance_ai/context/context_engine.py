from typing import Dict, Any, List
from django.contrib.auth import get_user_model
from platform_services.identity.models import Organization, Role
from .context_schema import AllianceAIContext

User = get_user_model()

class ContextEngine:
    """
    Resolves the secure execution context for an AI request.
    Extracts User, Tenant, Roles, and Permissions from the identity system.
    """

    @classmethod
    def build_context(cls, user: User, client_context: Dict[str, Any]) -> AllianceAIContext:
        """
        Builds the AllianceAIContext.
        `client_context` contains info sent from the frontend (module, route, etc.).
        `user` is the authenticated Django user.
        """
        # 1. Resolve Organization (Tenant)
        # Assuming user has a foreign key to organization or a profile.
        # We will safely mock this extraction depending on the actual identity model.
        # Based on typical Alliance OS identity setup:
        org_id = ""
        org_name = ""
        if hasattr(user, 'organization') and user.organization:
            org_id = str(user.organization.id)
            org_name = user.organization.name
        
        # 2. Resolve Roles & Permissions
        roles = []
        permissions = set()
        
        if user.is_superuser:
            roles.append("superuser")
        
        # Assuming user.roles.all() exists if using RBAC
        if hasattr(user, 'roles'):
            for role in user.roles.all():
                roles.append(role.name)
                for perm in role.permissions.all():
                    permissions.add(perm.code)
                    
        # 3. Extract UI context safely
        active_module = client_context.get("active_module")
        active_route = client_context.get("active_route")
        academic_year = client_context.get("academic_year")
        selected_object_id = client_context.get("selected_object_id")

        return AllianceAIContext(
            user_id=str(user.id),
            user_email=user.email,
            organization_id=org_id,
            organization_name=org_name,
            roles=roles,
            permissions=list(permissions),
            active_module=active_module,
            active_route=active_route,
            academic_year=academic_year,
            selected_object_id=selected_object_id
        )
