from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

@dataclass
class RunEvent:
    run_id: str
    event_id: str
    event_type: str
    state: str
    timestamp: str
    component: str
    status: str
    details: Dict[str, Any]
    parent_event_id: Optional[str] = None

    def to_dict(self):
        return asdict(self)

def utc_now():
    return datetime.now(timezone.utc).isoformat()
