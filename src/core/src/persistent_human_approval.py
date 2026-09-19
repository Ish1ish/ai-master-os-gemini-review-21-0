"""O46-S63 persisted human-approval state and resume support."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .human_approval_boundary import (
    ActionRisk,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalState,
    HumanApprovalBoundary,
)
from .human_approval_boundary_integration import GovernedAutonomousApprovalIntegration


@dataclass(frozen=True)
class ApprovalCheckpoint:
    action_id: str
    action_type: str
    risk: str
    summary: str
    request_state: str
    request_fingerprint: str
    cycle_trace_ids: tuple[str, ...]
    status: str
    decision_state: str = ApprovalState.AWAITING_APPROVAL.value
    approver_id: str | None = None
    decision_reason: str = "explicit_human_decision_required"
    decision_fingerprint: str = ""
    released: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["cycle_trace_ids"] = list(self.cycle_trace_ids)
        return payload

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ApprovalCheckpoint":
        return cls(
            action_id=str(raw["action_id"]),
            action_type=str(raw["action_type"]),
            risk=str(raw["risk"]),
            summary=str(raw["summary"]),
            request_state=str(raw["request_state"]),
            request_fingerprint=str(raw["request_fingerprint"]),
            cycle_trace_ids=tuple(str(x) for x in raw.get("cycle_trace_ids", [])),
            status=str(raw["status"]),
            decision_state=str(raw.get("decision_state", ApprovalState.AWAITING_APPROVAL.value)),
            approver_id=raw.get("approver_id"),
            decision_reason=str(raw.get("decision_reason", "explicit_human_decision_required")),
            decision_fingerprint=str(raw.get("decision_fingerprint", "")),
            released=bool(raw.get("released", False)),
        )


class ApprovalCheckpointStore:
    """Small atomic JSON checkpoint store for approval workflow state only."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> ApprovalCheckpoint | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return ApprovalCheckpoint.from_dict(data)

    def save(self, checkpoint: ApprovalCheckpoint) -> ApprovalCheckpoint:
        data = json.dumps(checkpoint.to_dict(), ensure_ascii=False, sort_keys=True, indent=2)
        fd, tmp_name = tempfile.mkstemp(prefix=self.path.name + ".", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        return checkpoint

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


class PersistentHumanApprovalIntegration:
    """S62 integration with durable approval checkpoint + restart resume."""

    def __init__(
        self,
        *,
        checkpoint_store: ApprovalCheckpointStore,
        integration: GovernedAutonomousApprovalIntegration | None = None,
    ) -> None:
        self.store = checkpoint_store
        self.integration = integration or GovernedAutonomousApprovalIntegration()
        self._rehydrate_checkpoint()

    def _rehydrate_checkpoint(self) -> ApprovalCheckpoint | None:
        checkpoint = self.store.load()
        if checkpoint is None:
            return None
        # Re-create the request and decision in the fresh in-memory boundary.
        self.integration.approval_boundary.request(
            action_id=checkpoint.action_id,
            action_type=checkpoint.action_type,
            risk=ActionRisk(checkpoint.risk),
            summary=checkpoint.summary,
        )
        if checkpoint.decision_state == ApprovalState.APPROVED.value:
            self.integration.approval_boundary.approve(
                action_id=checkpoint.action_id,
                approver_id=checkpoint.approver_id or "restored-approver",
            )
        elif checkpoint.decision_state == ApprovalState.REJECTED.value:
            self.integration.approval_boundary.reject(
                action_id=checkpoint.action_id,
                approver_id=checkpoint.approver_id or "restored-approver",
                reason=checkpoint.decision_reason,
            )
        return checkpoint

    def run_to_approval(self, *, topic: str = "O46 S63 approval persistence") -> ApprovalCheckpoint:
        existing = self.store.load()
        if existing is not None:
            return existing

        result = self.integration.run_to_approval(topic=topic)
        request = result.approval_request
        checkpoint = ApprovalCheckpoint(
            action_id=request.action_id,
            action_type=request.action_type,
            risk=request.risk.value,
            summary=request.summary,
            request_state=request.state.value,
            request_fingerprint=request.request_fingerprint,
            cycle_trace_ids=tuple(c.trace_id for c in result.cycles),
            status="AWAITING_APPROVAL",
        )
        return self.store.save(checkpoint)

    def approve(self, action_id: str, approver_id: str) -> ApprovalDecision:
        checkpoint = self.store.load()
        if checkpoint is None or checkpoint.action_id != action_id:
            return self.integration.approval_boundary.approve(action_id=action_id, approver_id=approver_id)
        decision = self.integration.approve(action_id, approver_id)
        updated = ApprovalCheckpoint(
            **{
                **checkpoint.to_dict(),
                "cycle_trace_ids": tuple(checkpoint.cycle_trace_ids),
                "status": "APPROVED" if decision.state == ApprovalState.APPROVED else decision.state.value,
                "decision_state": decision.state.value,
                "approver_id": decision.approver_id,
                "decision_reason": decision.reason,
                "decision_fingerprint": decision.decision_fingerprint,
                "released": decision.released,
            }
        )
        self.store.save(updated)
        return decision

    def reject(self, action_id: str, approver_id: str, reason: str = "human_rejected") -> ApprovalDecision:
        checkpoint = self.store.load()
        if checkpoint is None or checkpoint.action_id != action_id:
            return self.integration.approval_boundary.reject(action_id=action_id, approver_id=approver_id, reason=reason)
        decision = self.integration.reject(action_id, approver_id, reason)
        updated = ApprovalCheckpoint(
            **{
                **checkpoint.to_dict(),
                "cycle_trace_ids": tuple(checkpoint.cycle_trace_ids),
                "status": "REJECTED" if decision.state == ApprovalState.REJECTED else decision.state.value,
                "decision_state": decision.state.value,
                "approver_id": decision.approver_id,
                "decision_reason": decision.reason,
                "decision_fingerprint": decision.decision_fingerprint,
                "released": decision.released,
            }
        )
        self.store.save(updated)
        return decision

    def checkpoint_snapshot(self) -> Mapping[str, Any]:
        checkpoint = self.store.load()
        return checkpoint.to_dict() if checkpoint is not None else {}
