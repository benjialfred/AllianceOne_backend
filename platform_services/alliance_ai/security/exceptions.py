class SecurityGateError(Exception):
    """Base exception for all Security Gate errors (Fail-Closed)."""
    pass

class UnauthorizedToolError(SecurityGateError):
    """Raised when Grok tries to use a tool that doesn't exist or is not registered."""
    pass

class AuthenticationRequiredError(SecurityGateError):
    """Raised when the user is not authenticated."""
    pass

class TenantMismatchError(SecurityGateError):
    """Raised when trying to access a resource outside the user's organization."""
    pass

class PermissionDeniedError(SecurityGateError):
    """Raised when the user lacks the required RBAC permission for a tool."""
    pass

class InvalidArgumentError(SecurityGateError):
    """Raised when arguments fail schema or business validation."""
    pass

class ConfirmationExpiredError(SecurityGateError):
    """Raised when an action confirmation has expired."""
    pass

class ActionHashMismatchError(SecurityGateError):
    """Raised when the confirmed action hash doesn't match the current execution attempt."""
    pass
