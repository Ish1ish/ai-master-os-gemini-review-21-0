"""S8 persistent trace + memory handoff.

Persists a compact, structured Unified Run record and exposes a deterministic
memory-write proposal. The proposal is deliberately not committed automatically:
consequential memory/state changes remain reviewable.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping


class UnifiedRunPersistence:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.root / "unified_runs.jsonl"

    def _identity(self, run: Mapping[str, Any]) -> tuple[str, str]:
        run_id = str(run.get("run_id") or "")
        project_id = str(run.get("project_id") or "")
        if not run_id or not project_id:
            raise ValueError("run_id_and_project_id_are_required")
        return run_id, project_id

    def fingerprint(self, run: Mapping[str, Any]) -> str:
        run_id, project_id = self._identity(run)
        compact = {
            "run_id": run_id,
            "project_id": project_id,
            "strategy_id": run.get("strategy_id"),
            "status": run.get("status"),
            "next_decision": run.get("next_decision"),
        }
        return hashlib.sha256(
            json.dumps(compact, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    def persist(self, run: Mapping[str, Any]) -> Dict[str, Any]:
        run_id, project_id = self._identity(run)
        record = {
            "run_id": run_id,
            "project_id": project_id,
            "strategy_id": run.get("strategy_id"),
            "status": run.get("status"),
            "stage_count": run.get("stage_count"),
            "next_decision": dict(run.get("next_decision") or {}),
            "fingerprint": self.fingerprint(run),
        }

        existing = []
        if self.trace_path.exists():
            existing = [
                json.loads(line)
                for line in self.trace_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        for item in existing:
            if item.get("run_id") == run_id and item.get("project_id") == project_id:
                if item.get("fingerprint") == record["fingerprint"]:
                    return {
                        "status": "IDEMPOTENT_REPLAY",
                        "run_id": run_id,
                        "project_id": project_id,
                        "fingerprint": record["fingerprint"],
                        "path": str(self.trace_path),
                    }
                return {
                    "status": "CONFLICT",
                    "run_id": run_id,
                    "project_id": project_id,
                    "fingerprint": record["fingerprint"],
                    "existing_fingerprint": item.get("fingerprint"),
                    "path": str(self.trace_path),
                }

        with self.trace_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

        return {
            "status": "PERSISTED",
            "run_id": run_id,
            "project_id": project_id,
            "fingerprint": record["fingerprint"],
            "path": str(self.trace_path),
        }

    def get(self, run_id: str, project_id: str) -> Dict[str, Any] | None:
        if not self.trace_path.exists():
            return None
        for line in self.trace_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("run_id") == run_id and item.get("project_id") == project_id:
                return item
        return None


class UnifiedMemoryHandoff:
    """Builds a reviewable memory proposal; does not commit memory."""

    def propose(self, run: Mapping[str, Any]) -> Dict[str, Any]:
        run_id, project_id = UnifiedRunPersistence(Path("."))._identity(run)
        next_decision = dict(run.get("next_decision") or {})
        learning = dict((run.get("stages") or {}).get("LEARNING") or {})
        adaptation = dict((run.get("stages") or {}).get("ADAPTATION") or {})

        return {
            "status": "PROPOSAL_ONLY",
            "memory_write": False,
            "object_type": "UNIFIED_RUN_LESSON",
            "object_id": f"LES-{hashlib.sha256(run_id.encode()).hexdigest()[:12].upper()}",
            "scope": "project",
            "project_id": project_id,
            "run_id": run_id,
            "summary": learning.get("lesson", ""),
            "confidence": learning.get("evidence_sufficiency", "UNKNOWN"),
            "source_refs": [run_id],
            "next_decision": next_decision,
            "adaptation_recommendation": adaptation.get("recommendation"),
            "human_gate": True,
        }
