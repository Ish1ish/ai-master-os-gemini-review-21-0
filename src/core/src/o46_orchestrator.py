from __future__ import annotations

from typing import Any, Dict, Optional

from .o46_store import CycleStore


TERMINAL_EXECUTION = {"SUCCEEDED", "FAILED_TERMINAL", "BLOCKED", "CANCELLED", "RECOVERY_REQUIRED"}


class GovernedAutonomousLoop:
    """O46: bounded end-to-end loop across learning, governance and execution.

    O46 automates orchestration, not authority. Consequential actions remain paused
    until O44 approval is explicitly granted and O45 validates the exact approval.
    """

    def __init__(self, *, execution_service, cycle_store: CycleStore, experiment_service=None,
                 learning_provider=None):
        self.execution = execution_service
        self.store = cycle_store
        self.experiments = experiment_service
        self.learning_provider = learning_provider

    @staticmethod
    def _validate_plan(plan: Dict[str, Any]) -> Optional[str]:
        if not isinstance(plan, dict):
            return "plan_must_be_object"
        actions = plan.get("actions")
        if not isinstance(actions, list) or not actions:
            return "actions_required"
        seen_keys = set()
        for index, action in enumerate(actions):
            if not isinstance(action, dict):
                return f"action_{index}_must_be_object"
            for field in ("action", "tool_name", "payload", "idempotency_key"):
                if field not in action:
                    return f"action_{index}_{field}_required"
            key = str(action["idempotency_key"])
            if key in seen_keys:
                return "duplicate_action_idempotency_key"
            seen_keys.add(key)
            if not isinstance(action["payload"], dict):
                return f"action_{index}_payload_must_be_object"
        return None

    def _learning(self, project_id: str, experiment_id: Optional[str]) -> Dict[str, Any]:
        if self.learning_provider is None:
            return {"status": "UNAVAILABLE", "project_id": project_id}
        if hasattr(self.learning_provider, "get_learning_context"):
            return self.learning_provider.get_learning_context(project_id, current_experiment_id=experiment_id)
        if callable(self.learning_provider):
            return self.learning_provider(project_id)
        return {"status": "UNAVAILABLE", "project_id": project_id}

    def start_cycle(self, *, project_id: str, run_id: Optional[str], plan: Dict[str, Any],
                    idempotency_key: str, requested_by: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not project_id.strip():
            return {"status": "BAD_REQUEST", "reason": "project_id_required"}
        if not idempotency_key.strip():
            return {"status": "BAD_REQUEST", "reason": "idempotency_key_required"}
        if not requested_by.strip():
            return {"status": "BAD_REQUEST", "reason": "requested_by_required"}
        error = self._validate_plan(plan)
        if error:
            return {"status": "BAD_REQUEST", "reason": error}

        existing = self.store.by_idempotency(idempotency_key)
        if existing:
            return {"status": "IDEMPOTENT_REPLAY", "cycle": existing}

        experiment_id = plan.get("experiment_id")
        learning = self._learning(project_id, experiment_id)
        action_results = []
        execution_ids = []
        waiting = False
        blocked = False
        for item in plan["actions"]:
            action_context = dict(context or {})
            action_context.update(item.get("context") or {})
            action_context["o46_cycle_idempotency_key"] = idempotency_key
            out = self.execution.request(
                project_id=project_id,
                run_id=run_id,
                action=item["action"],
                tool_name=item["tool_name"],
                payload=item["payload"],
                context=action_context,
                idempotency_key=item["idempotency_key"],
                requested_by=requested_by,
            )
            action_results.append(out)
            execution = out.get("execution") or {}
            if execution.get("execution_id"):
                execution_ids.append(execution["execution_id"])
            if execution.get("state") == "AWAITING_APPROVAL":
                waiting = True
            if out.get("status") == "BLOCK" or execution.get("state") == "BLOCKED":
                blocked = True

        cycle = self.store.create(
            idempotency_key=idempotency_key,
            project_id=project_id,
            run_id=run_id,
            requested_by=requested_by,
            plan=plan,
            execution_ids=execution_ids,
            experiment_id=experiment_id,
        )
        self.store.transition(cycle["cycle_id"], "RUNNING", result={"actions": action_results, "learning_context": learning})
        if blocked:
            cycle = self.store.transition(cycle["cycle_id"], "BLOCKED", result={"actions": action_results})
            return {"status": "BLOCKED", "cycle": cycle}
        if waiting:
            cycle = self.store.transition(cycle["cycle_id"], "WAITING_HUMAN_APPROVAL", result={"actions": action_results})
            return {"status": "WAITING_HUMAN_APPROVAL", "cycle": cycle}
        return self._drive(cycle["cycle_id"])

    def _drive(self, cycle_id: str) -> Dict[str, Any]:
        cycle = self.store.get(cycle_id)
        if not cycle:
            return {"status": "NOT_FOUND", "cycle_id": cycle_id}
        results = []
        waiting = False
        blocked = False
        recovery = False
        for execution_id in cycle["execution_ids"]:
            result = self.execution.execute_once(execution_id)
            results.append(result)
            status = result.get("status")
            if status in {"PENDING", "IN_PROGRESS_OR_NOT_READY"}:
                waiting = True
            elif status in {"BLOCKED", "DENY"}:
                blocked = True
            elif status == "RECOVERY_REQUIRED":
                recovery = True
            elif status == "FAILED":
                if (result.get("execution") or {}).get("state") == "RECOVERY_REQUIRED":
                    recovery = True
                elif (result.get("execution") or {}).get("state") == "FAILED_TERMINAL":
                    blocked = True

        if recovery:
            cycle = self.store.transition(cycle_id, "RECOVERY_REQUIRED", result={"executions": results})
            return {"status": "RECOVERY_REQUIRED", "cycle": cycle}
        if blocked:
            cycle = self.store.transition(cycle_id, "BLOCKED", result={"executions": results})
            return {"status": "BLOCKED", "cycle": cycle}
        if waiting:
            cycle = self.store.transition(cycle_id, "WAITING_HUMAN_APPROVAL", result={"executions": results})
            return {"status": "WAITING_HUMAN_APPROVAL", "cycle": cycle}

        if not all((r.get("status") in {"SUCCEEDED", "IDEMPOTENT_REPLAY"} for r in results)):
            cycle = self.store.transition(cycle_id, "FAILED", result={"executions": results})
            return {"status": "FAILED", "cycle": cycle}

        cycle = self.store.transition(cycle_id, "EVIDENCE_PENDING", result={"executions": results})
        if cycle.get("experiment_id") and self.experiments is not None:
            return {"status": "EVIDENCE_PENDING", "cycle": cycle}

        cycle = self.store.transition(cycle_id, "COMPLETE", result={"executions": results, "learning": "no_experiment_attached"})
        return {"status": "COMPLETE", "cycle": cycle}

    def resume(self, cycle_id: str) -> Dict[str, Any]:
        cycle = self.store.get(cycle_id)
        if not cycle:
            return {"status": "NOT_FOUND", "cycle_id": cycle_id}
        if cycle["state"] != "WAITING_HUMAN_APPROVAL":
            if cycle["state"] == "COMPLETE":
                return {"status": "IDEMPOTENT_REPLAY", "cycle": cycle}
            return {"status": "CONFLICT", "state": cycle["state"], "cycle_id": cycle_id}
        blocked = False
        pending = False
        for execution_id in cycle["execution_ids"]:
            item = self.execution.receipts.get(execution_id)
            if not item:
                blocked = True
                continue
            if item["state"] == "AWAITING_APPROVAL":
                verdict = self.execution.approve_and_ready(execution_id)
                if verdict.get("state") != "READY":
                    pending = True
        if pending:
            return {"status": "WAITING_HUMAN_APPROVAL", "cycle": self.store.get(cycle_id)}
        if blocked:
            return {"status": "BLOCKED", "cycle": self.store.transition(cycle_id, "BLOCKED", error={"code": "execution_missing"})}
        return self._drive(cycle_id)

    def record_evidence_and_learn(self, cycle_id: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        cycle = self.store.get(cycle_id)
        if not cycle:
            return {"status": "NOT_FOUND", "cycle_id": cycle_id}
        if cycle["state"] != "EVIDENCE_PENDING":
            return {"status": "CONFLICT", "state": cycle["state"]}
        if not cycle.get("experiment_id") or self.experiments is None:
            return {"status": "CONFLICT", "reason": "experiment_not_attached"}
        saved = self.experiments.record_evidence(cycle["experiment_id"], evidence)
        if saved.get("status") not in {"OK", "UPDATED", "PASS"} and "evidence" not in saved:
            return {"status": "EVIDENCE_REJECTED", "result": saved}
        cycle = self.store.transition(cycle_id, "LEARNING", result={"evidence": saved})
        evaluation = self.experiments.evaluate(cycle["experiment_id"])
        decision = (evaluation.get("evaluation") or {}).get("decision")
        if decision == "GO":
            next_cycle = {"route": "BOUNDED_NEXT_STEP", "reason": "validated_thresholds_met"}
            state = "COMPLETE"
        elif decision == "REFINE":
            next_cycle = {"route": "REFINE_BEFORE_REBUILD", "reason": "threshold_missed"}
            state = "COMPLETE"
        elif decision == "NO-GO":
            next_cycle = {"route": "ROUTE_TO_NEXT_HYPOTHESIS", "reason": "hypothesis_rejected"}
            state = "COMPLETE"
        else:
            next_cycle = {"route": "COLLECT_MORE_EVIDENCE", "reason": "experiment_inconclusive"}
            state = "EVIDENCE_PENDING"
        cycle = self.store.transition(cycle_id, state, result={"evaluation": evaluation}, next_cycle=next_cycle)
        return {"status": state, "cycle": cycle, "evaluation": evaluation}

    def events(self, cycle_id: str) -> list[Dict[str, Any]]:
        return self.store.events(cycle_id)

    def close(self) -> None:
        self.store.close()
