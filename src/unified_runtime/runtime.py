"""S9 Unified Run Coordinator.

Composes the verified GoldenUnifiedRun with persistent trace and memory handoff
so one host-level call returns the complete journey plus durable trace status
and an explicit reviewable memory proposal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .golden_run import GoldenUnifiedRun
from .persistence import UnifiedMemoryHandoff, UnifiedRunPersistence


class UnifiedRunCoordinator:
    def __init__(self, persistence_root: str | Path):
        self.golden = GoldenUnifiedRun()
        self.persistence = UnifiedRunPersistence(persistence_root)
        self.memory = UnifiedMemoryHandoff()

    def run(self, *, run_id: str, project_id: str, strategy_id: str) -> Dict[str, Any]:
        result = self.golden.run(
            run_id=run_id,
            project_id=project_id,
            strategy_id=strategy_id,
        )

        trace = self.persistence.persist(result)
        memory_proposal = self.memory.propose(result)

        result = dict(result)
        result["persistence"] = trace
        result["memory_proposal"] = memory_proposal
        result["coordinator_status"] = (
            "PERSISTED_WITH_REVIEWABLE_MEMORY"
            if trace["status"] in {"PERSISTED", "IDEMPOTENT_REPLAY"}
            else "PERSISTENCE_BLOCKED"
        )
        return result
