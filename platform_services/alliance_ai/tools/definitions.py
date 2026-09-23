from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Union

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ActionScope(Enum):
    READ = "READ"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    FINANCIAL = "FINANCIAL"
    EXTERNAL_SIDE_EFFECT = "EXTERNAL_SIDE_EFFECT"

@dataclass
class AIToolPolicy:
    """
    Defines the contract and security policy for a capability exposed by a Bounded Context to Alliance AI.
    """
    name: str                       
    description: str                
    input_schema: Dict[str, Any]    
    output_schema: Dict[str, Any]   
    required_permissions: Union[str, List[str], Any] # Can be ANY or ALL composite
    risk_level: RiskLevel           
    action_scope: ActionScope = ActionScope.READ
    mutation: bool = False
    requires_confirmation: bool = False 
    object_scope: str = "organization"
    module_slug: str = None  # NEW: The slug of the module this tool belongs to
    handler: Callable = None

# For backwards compatibility during transition
AIToolDefinition = AIToolPolicy
