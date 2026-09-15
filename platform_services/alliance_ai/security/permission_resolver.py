from typing import List, Optional
from platform_services.identity.models import User, Membership, Role

# -----------------------------------------------------------------------------
# EXPLICIT POLICY LAYER
# -----------------------------------------------------------------------------
# As discovered during the P0 audit, the Django models (Role) do not currently
# map to granular string-based permissions (e.g. "finance.invoice.create") 
# in the database.
# 
# Per architectural rule #2: this explicit policy layer constitutes the current
# source of authority for RBAC until a dynamic RolePermission table is created.
# -----------------------------------------------------------------------------

ROLE_PERMISSIONS_MAPPING = {
    "ADMINISTRATOR": [
        "education.student.read",
        "education.student.create",
        "education.student.delete",
        "finance.invoice.read",
        "finance.invoice.create",
        "finance.refund",
        "system.admin"
    ],
    "MANAGER": [
        "education.student.read",
        "education.student.create",
        "finance.invoice.read",
        "finance.invoice.create"
    ],
    "SALES_AGENT": [
        "finance.invoice.read",
        "finance.invoice.create"
    ],
    "TEACHER": [
        "education.student.read"
    ]
}

class PermissionResolver:
    """
    Resolves the actual permissions for a user within a specific organization context.
    """

    @classmethod
    def resolve_membership(cls, user_id: str, organization_id: str) -> Optional[Membership]:
        """
        Ensures the user has an active membership in the target organization.
        """
        try:
            # We assume user is active and membership exists.
            membership = Membership.objects.select_related('role').get(
                user_id=user_id,
                organization_id=organization_id,
                user__is_active=True
            )
            return membership
        except Membership.DoesNotExist:
            return None

    @classmethod
    def resolve_permissions(cls, user_id: str, organization_id: str) -> List[str]:
        """
        Returns the list of permissions the user holds in this organization.
        """
        membership = cls.resolve_membership(user_id, organization_id)
        if not membership or not membership.role:
            return []
            
        # In a dynamic system, this would query RolePermission objects.
        # Here we use the explicit policy map above.
        role_name = membership.role.name.upper()
        return ROLE_PERMISSIONS_MAPPING.get(role_name, [])

    @classmethod
    def has_permission(cls, user_id: str, organization_id: str, required_permission: str) -> bool:
        """
        Checks if the user holds a specific permission.
        """
        permissions = cls.resolve_permissions(user_id, organization_id)
        return required_permission in permissions
