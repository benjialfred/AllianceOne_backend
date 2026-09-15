import enum
import hashlib
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any

class Decision(enum.Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    REQUIRE_ADDITIONAL_AUTH = "REQUIRE_ADDITIONAL_AUTH"

class ActionScope(enum.Enum):
    READ = "READ"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    FINANCIAL = "FINANCIAL"
    EXTERNAL_SIDE_EFFECT = "EXTERNAL_SIDE_EFFECT"

@dataclass
class ApprovalDecision:
    decision: Decision
    requires_confirmation: bool
    reason: Optional[str]
    risk_level: str
    policy: str
    user_id: Optional[str]
    organization_id: Optional[str]
    tool: str
    action_hash: Optional[str] = None
    reason_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "requires_confirmation": self.requires_confirmation,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "policy": self.policy,
            "user_id": str(self.user_id) if self.user_id else None,
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "tool": self.tool,
            "action_hash": self.action_hash,
            "reason_code": self.reason_code
        }

def generate_canonical_action_hash(mission_id: str, organization_id: str, user_id: str, tool_name: str, arguments: Dict[str, Any], policy_version: str = "1.0") -> str:
    """
    Generates a deterministic SHA-256 hash representing a specific action to ensure
    arguments are not tampered with after confirmation.
    """
    canonical_action = {
        "mission_id": str(mission_id),
        "organization_id": str(organization_id),
        "user_id": str(user_id),
        "tool_name": tool_name,
        "arguments": arguments,  # Ensure arguments is serialized cleanly
        "policy_version": policy_version
    }
    
    # Sort keys to ensure deterministic representation
    canonical_json = json.dumps(canonical_action, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
