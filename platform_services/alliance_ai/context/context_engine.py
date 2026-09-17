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
        org_id = ""
        org_name = ""
        target_org_id = client_context.get("organization_id") or client_context.get("tenant_id")

        if hasattr(user, 'organization') and user.organization:
            org_id = str(user.organization.id)
            org_name = user.organization.name
        elif hasattr(user, 'memberships'):
            membership = None
            if target_org_id:
                membership = user.memberships.filter(organization_id=target_org_id).select_related('organization', 'role').first()
            if not membership:
                membership = user.memberships.select_related('organization', 'role').first()
            if membership and membership.organization:
                org_id = str(membership.organization.id)
                org_name = membership.organization.name

        # 2. Resolve Roles & Permissions
        roles = []
        permissions = set()
        
        if user.is_superuser:
            roles.append("superuser")
        
        # Support user.roles (for mock objects or direct role attachments)
        if hasattr(user, 'roles'):
            for role in user.roles.all():
                roles.append(role.name)
                if hasattr(role, 'permissions'):
                    for perm in role.permissions.all():
                        permissions.add(perm.code)

        # Support real database user.memberships for active organization
        if hasattr(user, 'memberships') and org_id:
            try:
                m = user.memberships.filter(organization_id=org_id).select_related('role').first()
                if m and m.role:
                    if m.role.name not in roles:
                        roles.append(m.role.name)
                    from platform_services.alliance_ai.security.permission_resolver import PermissionResolver
                    user_perms = PermissionResolver.resolve_permissions(str(user.id), org_id)
                    for p in user_perms:
                        permissions.add(p)
            except Exception:
                pass
                    
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
