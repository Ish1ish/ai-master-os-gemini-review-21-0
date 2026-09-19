from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

@dataclass
class ApprovalRequest:
    approval_id: str
    run_id: str
    action: str
    risk: str
    reason: str
    context: Dict[str, Any]
    requested_by: str = "orchestrator"
    status: str = "PENDING"
    decision_by: Optional[str] = None
    decision_reason: Optional[str] = None
    created_at: Optional[str] = None
    decided_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
