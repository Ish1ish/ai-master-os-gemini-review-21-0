"""S5 bridge: Governed execution gate -> execution -> outcome evidence.

This adapter deliberately keeps the consequential-action boundary explicit.
A callable executor is injected by the host runtime. S5 can safely execute
non-consequential/simulated work; consequential work requires an explicit
APPROVED approval status and an authorization flag.

The outcome is normalized into a traceable result without mutating governance
state or memory.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, Mapping


class UnifiedExecutionOutcomeAdapter:
    EXECUTABLE_POSTURE = "PROCEED_TO_EXECUTION_GATE"

    def execution_id(self, *, run_id: str, project_id: str, action_key: str) -> str:
        seed = f"{run_id}|{project_id}|{action_key}"
        return "EXE-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16].upper()

    def run(
        self,
        governance: Mapping[str, Any],
        *,
        run_id: str,
        project_id: str,
        action_key: str,
        executor: Callable[[], Mapping[str, Any]] | None = None,
        consequential: bool = False,
        approval_status: str | None = None,
        authorized: bool = False,
    ) -> Dict[str, Any]:
        if not isinstance(governance, Mapping):
            raise TypeError("governance_must_be_mapping")
        if not run_id or not project_id or not action_key:
            raise ValueError("run_identity_and_action_key_are_required")

        execution_id = self.execution_id(
            run_id=run_id, project_id=project_id, action_key=action_key
        )

        if governance.get("status") != "GOVERNED":
            return self._blocked(execution_id, run_id, project_id, "governance_not_ready")

        if governance.get("posture") != self.EXECUTABLE_POSTURE:
            return self._blocked(
                execution_id, run_id, project_id,
                f"posture_not_executable:{governance.get('posture')}"
            )

        if consequential and (approval_status != "APPROVED" or not authorized):
            return self._blocked(
                execution_id, run_id, project_id,
                "consequential_action_requires_approved_authorized_gate"
            )

        if executor is None:
            executor = lambda: {"status": "SUCCEEDED", "output": {"mode": "SIMULATED"}}

        try:
            raw = executor()
        except Exception as exc:
            return self._outcome(
                execution_id, run_id, project_id,
                execution_status="FAILED",
                outcome_status="FAILURE",
                output={},
                error=f"{type(exc).__name__}:{exc}",
                external_action_executed=False,
            )

        if not isinstance(raw, Mapping):
            return self._outcome(
                execution_id, run_id, project_id,
                execution_status="FAILED",
                outcome_status="FAILURE",
                output={},
                error="executor_result_must_be_mapping",
                external_action_executed=False,
            )

        execution_status = str(raw.get("status") or "").upper()
        success = execution_status == "SUCCEEDED"
        return self._outcome(
            execution_id, run_id, project_id,
            execution_status=execution_status or "FAILED",
            outcome_status="SUCCESS" if success else "FAILURE",
            output=dict(raw.get("output") or {}),
            error=str(raw.get("error") or ""),
            external_action_executed=bool(consequential),
        )

    def _blocked(self, execution_id: str, run_id: str, project_id: str, reason: str) -> Dict[str, Any]:
        return self._outcome(
            execution_id, run_id, project_id,
            execution_status="BLOCKED",
            outcome_status="BLOCKED",
            output={},
            error=reason,
            external_action_executed=False,
        )

    def _outcome(
        self,
        execution_id: str,
        run_id: str,
        project_id: str,
        *,
        execution_status: str,
        outcome_status: str,
        output: Dict[str, Any],
        error: str,
        external_action_executed: bool,
    ) -> Dict[str, Any]:
        payload = {
            "execution_id": execution_id,
            "run_id": run_id,
            "project_id": project_id,
            "execution_status": execution_status,
            "outcome_status": outcome_status,
            "output": output,
            "error": error,
            "external_action_executed": external_action_executed,
            "governance_mutation": False,
            "outcome_evidence": {
                "status": outcome_status,
                "execution_id": execution_id,
                "observable": True,
                "output_present": bool(output),
                "error_present": bool(error),
            },
        }
        payload["outcome_fingerprint"] = hashlib.sha256(
            json.dumps(payload["outcome_evidence"], sort_keys=True).encode("utf-8")
        ).hexdigest()
        return payload
