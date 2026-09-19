from __future__ import annotations

import json
from pathlib import Path
import py_compile

from core.src.execution_outcome_intelligence import ExecutionOutcomeIntelligence, OutcomeObservation

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "core" / "src" / "execution_outcome_intelligence.py"
TEST = ROOT / "tests" / "test_s47_execution_outcome_intelligence.py"
S46 = ROOT / "src" / "core" / "src" / "governed_action_integration.py"

checks = {
    "outcome_intelligence_present": MODULE.exists(),
    "s46_integration_present": S46.exists(),
    "expected_actual_contract": False,
    "success_feedback": False,
    "failure_feedback": False,
    "inconclusive_not_decision_driving": False,
    "learning_signal_traceable": False,
    "next_decision_routing": False,
    "idempotent_outcome_receipt": False,
    "memory_write_blocked": False,
    "compileall": False,
    "targeted_tests": False,
}

engine = ExecutionOutcomeIntelligence()
success = engine.record(OutcomeObservation("R-GATE-1", "P1", "A1", "ok", "ok", ("E1",)))
checks["success_feedback"] = success.status == "SUCCESS" and success.decision_feedback == "SUPPORTS_DECISION"
checks["expected_actual_contract"] = success.expected_vs_actual_match is True
checks["learning_signal_traceable"] = bool(success.learning_signal and success.learning_signal.evidence_refs == ("E1",))
checks["next_decision_routing"] = success.next_decision == "BOUNDED_NEXT_STEP"

failure = engine.record(OutcomeObservation("R-GATE-2", "P1", "A2", "ok", "bad", ("E2",)))
checks["failure_feedback"] = failure.status == "FAILURE" and failure.next_decision == "REASSESS_OR_CHANGE"

inconclusive = engine.record(OutcomeObservation("R-GATE-3", "P1", "A3", "ok", None, ("E3",)))
checks["inconclusive_not_decision_driving"] = inconclusive.status == "INCONCLUSIVE" and inconclusive.learning_signal is None and inconclusive.next_decision == "COLLECT_MORE_EVIDENCE"

replay = engine.record(OutcomeObservation("R-GATE-1", "P1", "A1", "ok", "bad", ("E9",)))
checks["idempotent_outcome_receipt"] = replay == success and len(engine.snapshot()) == 3
checks["memory_write_blocked"] = success.memory_write_executed is False

try:
    py_compile.compile(str(MODULE), doraise=True)
    checks["compileall"] = True
except Exception:
    checks["compileall"] = False

ns = {}
exec(compile(TEST.read_text(encoding="utf-8"), str(TEST), "exec"), ns)
ns["run_all"]()
checks["targeted_tests"] = True

status = "PASS" if all(checks.values()) else "FAIL"
print("S47_EXECUTION_OUTCOME_INTELLIGENCE_" + status)
print(json.dumps({
    "release": "O45-S47",
    "status": status,
    "checks": checks,
    "outcome_summary": {
        "success": success.status,
        "failure": failure.status,
        "inconclusive": inconclusive.status,
        "success_next_decision": success.next_decision,
        "failure_next_decision": failure.next_decision,
        "inconclusive_next_decision": inconclusive.next_decision,
    },
    "external_action_executed": False,
    "memory_write_executed": False,
    "internet_facing_production_approval": False,
    "notes": [k for k, v in checks.items() if not v],
}, indent=2))
