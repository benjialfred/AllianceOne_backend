from enum import Enum
from dataclasses import dataclass
from typing import Callable, List, Dict, Any

class RiskLevel(Enum):
    LOW = "LOW"           # Read-only operations, safe
    MEDIUM = "MEDIUM"     # Creates drafts, non-destructive
    HIGH = "HIGH"         # Modifies data, sends emails
    CRITICAL = "CRITICAL" # Deletions, financial transactions, massive updates

@dataclass
class AIToolDefinition:
    """
    Defines the contract for a capability exposed by a Bounded Context to Alliance AI.
    """
    name: str                       # e.g., "education.search_students"
    description: str                # e.g., "Search for students by name or class"
    input_schema: Dict[str, Any]    # JSON Schema for inputs
    output_schema: Dict[str, Any]   # JSON Schema for outputs (optional)
    required_permissions: List[str] # e.g., ["education.student.read"]
    risk_level: RiskLevel           # Determines if approval is needed
    handler: Callable               # The actual python function to call
    requires_confirmation: bool = False # Overrides risk level if explicitly set to True
