from typing import Dict, Any, List

class EventNormalizer:
    REQUIRED = ["event_id", "event_type", "timestamp", "properties"]

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        missing = [k for k in self.REQUIRED if k not in raw]
        if missing:
            raise ValueError(f"missing event fields: {missing}")
        return {
            "event_id": str(raw["event_id"]),
            "event_type": str(raw["event_type"]),
            "timestamp": str(raw["timestamp"]),
            "user_id": raw.get("user_id"),
            "session_id": raw.get("session_id"),
            "properties": dict(raw.get("properties") or {}),
        }

    def normalize_many(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.normalize(e) for e in events]
