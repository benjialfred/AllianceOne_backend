import enum
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

class ExecutionStatus(enum.Enum):
    PENDING = "PENDING"
    WAITING_FOR_DEPENDENCY = "WAITING_FOR_DEPENDENCY"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"

@dataclass
class ExecutionStep:
    tool_name: str
    arguments: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    step_id: str = field(default_factory=lambda: f"step_{uuid.uuid4().hex[:8]}")
    status: ExecutionStatus = ExecutionStatus.PENDING
    output: Any = None
    error: Optional[str] = None
    requires_confirmation: bool = False
    verification_status: Optional[str] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "requires_confirmation": self.requires_confirmation,
            "verification_status": self.verification_status,
            "execution_metadata": self.execution_metadata
        }

@dataclass
class ExecutionPlan:
    user_request: str
    organization_id: str
    plan_id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: ExecutionStatus = ExecutionStatus.PENDING
    steps: List[ExecutionStep] = field(default_factory=list)
    final_result: Optional[Any] = None

    def get_step(self, step_id: str) -> Optional[ExecutionStep]:
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
        
    def get_steps_by_status(self, status: ExecutionStatus) -> List[ExecutionStep]:
        return [s for s in self.steps if s.status == status]

    def add_step(self, step: ExecutionStep) -> None:
        self.steps.append(step)
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "user_request": self.user_request,
            "organization_id": str(self.organization_id),
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "steps": [step.to_dict() for step in self.steps],
            "final_result": self.final_result
        }
