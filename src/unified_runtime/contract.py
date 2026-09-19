from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Dict, List, Optional


class UnifiedRunError(ValueError):
    pass


class StageStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


STAGES = (
    "INTENT",
    "UNDERSTAND",
    "ROUTE",
    "EVIDENCE",
    "DECISION",
    "EVALUATION",
    "GOVERNANCE",
    "EXECUTION",
    "OUTCOME",
    "FEEDBACK",
    "LEARNING",
    "ADAPTATION",
    "NEXT_DECISION",
)

_TERMINAL = {StageStatus.FAILED, StageStatus.BLOCKED, StageStatus.CANCELLED}


@dataclass
class UnifiedStage:
    name: str
    status: StageStatus = StageStatus.NOT_STARTED
    data: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None
    trace_id: Optional[str] = None


@dataclass
class UnifiedRun:
    project_id: str
    intent: str
    run_id: str
    stages: Dict[str, UnifiedStage] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, project_id: str, intent: str, run_id: Optional[str] = None) -> "UnifiedRun":
        if not isinstance(project_id, str) or not project_id.strip():
            raise UnifiedRunError("project_id is required")
        if not isinstance(intent, str) or not intent.strip():
            raise UnifiedRunError("intent is required")
        canonical = f"{project_id.strip()}|{intent.strip()}"
        rid = run_id or f"UR-{sha256(canonical.encode('utf-8')).hexdigest()[:20].upper()}"
        stages = {name: UnifiedStage(name=name) for name in STAGES}
        return cls(project_id=project_id.strip(), intent=intent.strip(), run_id=rid, stages=stages)

    def _stage(self, name: str) -> UnifiedStage:
        if name not in STAGES:
            raise UnifiedRunError(f"unknown stage: {name}")
        return self.stages[name]

    def _index(self, name: str) -> int:
        return STAGES.index(name)

    def can_start(self, name: str) -> bool:
        stage = self._stage(name)
        if stage.status != StageStatus.NOT_STARTED:
            return False
        idx = self._index(name)
        if idx == 0:
            return True
        prev = self.stages[STAGES[idx - 1]]
        return prev.status == StageStatus.SUCCEEDED

    def start(self, name: str, trace_id: Optional[str] = None) -> UnifiedStage:
        if not self.can_start(name):
            raise UnifiedRunError(f"stage cannot start: {name}")
        stage = self._stage(name)
        stage.status = StageStatus.RUNNING
        stage.trace_id = trace_id or self.run_id
        return stage

    def finish(self, name: str, data: Optional[Dict[str, Any]] = None) -> UnifiedStage:
        stage = self._stage(name)
        if stage.status != StageStatus.RUNNING:
            raise UnifiedRunError(f"stage is not running: {name}")
        stage.status = StageStatus.SUCCEEDED
        stage.data = dict(data or {})
        return stage

    def stop(self, name: str, status: StageStatus, reason: str) -> UnifiedStage:
        if status not in _TERMINAL:
            raise UnifiedRunError("stop status must be FAILED, BLOCKED, or CANCELLED")
        stage = self._stage(name)
        if stage.status != StageStatus.RUNNING:
            raise UnifiedRunError(f"stage is not running: {name}")
        stage.status = status
        stage.reason = reason.strip() if isinstance(reason, str) else str(reason)
        return stage

    @property
    def current_stage(self) -> Optional[str]:
        for name in STAGES:
            if self.stages[name].status == StageStatus.RUNNING:
                return name
        for name in STAGES:
            if self.stages[name].status == StageStatus.NOT_STARTED:
                return name
        return None

    @property
    def terminal(self) -> bool:
        return any(s.status in _TERMINAL for s in self.stages.values())

    def snapshot(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "intent": self.intent,
            "current_stage": self.current_stage,
            "terminal": self.terminal,
            "stages": {
                name: {
                    "status": stage.status.value,
                    "data": dict(stage.data),
                    "reason": stage.reason,
                    "trace_id": stage.trace_id,
                }
                for name, stage in self.stages.items()
            },
            "metadata": dict(self.metadata),
        }
