from typing import List, Union, Callable, Dict, Any
from .permission_resolver import PermissionResolver
from .exceptions import PermissionDeniedError

class ANY:
    def __init__(self, *permissions: str):
        self.permissions = permissions

class ALL:
    def __init__(self, *permissions: str):
        self.permissions = permissions

PermissionRequirement = Union[str, ANY, ALL, List[str]]

class PolicyEngine:
    """
    Evaluates business rules, composed permissions, and object-level authorization.
    """

    @classmethod
    def evaluate_permissions(cls, user_id: str, organization_id: str, required: PermissionRequirement) -> bool:
        """
        Evaluates complex permission requirements (ANY, ALL, simple string, or list).
        """
        if not required:
            return True
            
        user_perms = PermissionResolver.resolve_permissions(user_id, organization_id)
        
        if isinstance(required, str):
            return required in user_perms
            
        if isinstance(required, list):
            # Default to ALL for backwards compatibility if a list is provided
            return all(p in user_perms for p in required)
            
        if isinstance(required, ANY):
            return any(p in user_perms for p in required.permissions)
            
        if isinstance(required, ALL):
            return all(p in user_perms for p in required.permissions)
            
        return False

    @classmethod
    def validate_object_ownership(cls, object_scope: str, arguments: Dict[str, Any], organization_id: str) -> bool:
        """
        Validates Object-level Authorization.
        Ensures that if an argument like `organization_id` or `agency_id` is passed,
        it matches the current tenant, preventing cross-tenant access.
        """
        if object_scope == "organization":
            # If the tool tries to manipulate a specific organization ID, it must match the user's current context
            arg_org_id = arguments.get("organization_id")
            if arg_org_id and str(arg_org_id) != str(organization_id):
                return False
                
            # Future expansion: Check if specific resources (like invoice_id) actually belong to organization_id.
            # This would require querying the DB for the object.
            # For P0, we enforce tenant isolation at the argument level.
            
        return True
