from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, Any, List

class MemoryStore:
    def __init__(self):
        self._objects: Dict[str, List[Dict[str, Any]]] = {}

    def write(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        required = ["object_type", "object_id", "version", "project_id",
                    "summary", "scope", "confidence"]
        missing = [k for k in required if k not in obj]
        if missing:
            raise ValueError(f"missing memory fields: {missing}")

        obj = deepcopy(obj)
        obj.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        obj.setdefault("status", "active")
        obj.setdefault("source_refs", [])
        obj.setdefault("supersedes", None)
        history = self._objects.setdefault(obj["object_id"], [])

        if history and obj["version"] == history[-1]["version"]:
            comparable_new = dict(obj)
            comparable_existing = dict(history[-1])
            comparable_new.pop("created_at", None)
            comparable_existing.pop("created_at", None)
            if comparable_new == comparable_existing:
                return deepcopy(history[-1])
            raise ValueError("memory version conflict")
        if history:
            obj["supersedes"] = f'{history[-1]["object_id"]}:{history[-1]["version"]}'
        else:
            obj.setdefault("supersedes", None)

        history.append(obj)
        return deepcopy(obj)

    def latest(self, object_id):
        h = self._objects.get(object_id, [])
        return deepcopy(h[-1]) if h else None

    def history(self, object_id):
        return deepcopy(self._objects.get(object_id, []))

    def list_by_project(self, project_id, limit=100):
        items = []
        for history in self._objects.values():
            if history and history[-1].get("project_id") == project_id:
                items.append(deepcopy(history[-1]))
        return items[:max(1, int(limit))]
