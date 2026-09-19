from typing import Dict, Any, List
from .events import RunEvent, utc_now

class AuditLog:
    def __init__(self):
        self._events: List[RunEvent] = []
        self._counter = 0

    def append(self, run_id: str, event_type: str, state: str, component: str,
               status: str, details: Dict[str, Any], parent_event_id=None):
        self._counter += 1
        event = RunEvent(
            run_id=run_id,
            event_id=f"EV-{self._counter:06d}",
            event_type=event_type,
            state=state,
            timestamp=utc_now(),
            component=component,
            status=status,
            details=details,
            parent_event_id=parent_event_id,
        )
        self._events.append(event)
        return event

    def for_run(self, run_id: str):
        return [e.to_dict() for e in self._events if e.run_id == run_id]

    def all(self):
        return [e.to_dict() for e in self._events]
