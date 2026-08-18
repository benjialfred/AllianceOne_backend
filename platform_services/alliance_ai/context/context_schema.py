from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class AllianceAIContext:
    """
    Represents the secure context under which an Alliance AI action is executed.
    This guarantees that the AI never exceeds the user's permissions or organization boundaries.
    """
    user_id: str
    user_email: str
    organization_id: str
    organization_name: str
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    
    # UI / Navigation context
    active_module: Optional[str] = None
    active_route: Optional[str] = None
    academic_year: Optional[str] = None
    selected_object_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_email": self.user_email,
            "organization_id": self.organization_id,
            "organization_name": self.organization_name,
            "roles": self.roles,
            "permissions": self.permissions,
            "active_module": self.active_module,
            "active_route": self.active_route,
            "academic_year": self.academic_year,
            "selected_object_id": self.selected_object_id
        }

    def has_permission(self, permission: str) -> bool:
        """
        Check if the context includes a specific permission.
        """
        # Superadmin override or explicit permission check
        if "superuser" in self.roles:
            return True
        return permission in self.permissions
