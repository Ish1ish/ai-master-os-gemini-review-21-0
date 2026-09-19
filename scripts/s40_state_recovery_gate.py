from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.src.approval_store import ApprovalStore
from core.src.execution_observability import ExecutionObservabilityStore
from core.src.jobs import JobStore
from core.src.decision_memory import CounterfactualDecisionMemory
from core.src.operator_store import OperatorStore
from core.src.queue import DurableQueue
from core.src.state_recovery import backup_sqlite_files, restore_sqlite_files

CHECKS = {}
NOTES = []
NAMES = ["jobs.sqlite3", "queue.sqlite3", "approvals.sqlite3", "operator.sqlite3", "memory.sqlite3", "audit.sqlite3"]


def seed_state(root: Path):
    jobs = JobStore(str(root / NAMES[0]))
    jobs.create("JOB-S40", "PROJ-S40", "state recovery drill", language="en")
    jobs.set_status("JOB-S40", "COMPLETE", result={"marker": "S40"})
    queue = DurableQueue(str(root / NAMES[1]))
    queue.enqueue("JOB-S40", {"marker": "S40"})
    queue.complete("JOB-S40", {"queue": "COMPLETE"})
    approvals = ApprovalStore(str(root / NAMES[2]))
    approval = approvals.create("JOB-S40", "publish_public_content", {"marker": "S40"}, requested_by="operator-01")
    approvals.decide(approval["approval_id"], "REJECTED", "operator-01", "drill only")
    operator = OperatorStore(str(root / NAMES[3]))
    operator.record("operator-01", "backup_drill", "JOB-S40", {"marker": "S40"})
    memory = CounterfactualDecisionMemory(str(root / NAMES[4]))
    pred = memory.record_prediction(project_id="PROJ-S40", requested_by="operator-01", prediction={"plan_hash": "S40-PLAN", "decision": "REVIEW", "risk": "LOW", "actions": [], "side_effects": "NONE"})
    memory.observe_outcome(prediction_id=pred["prediction_id"], actual={"decision": "REVIEW", "risk": "LOW"})
    audit = ExecutionObservabilityStore(str(root / NAMES[5]))
    audit.record_event(project_id="PROJ-S40", run_id="JOB-S40", decision_plan_id="PLAN-S40", intent_id="INTENT-S40", execution_id="EXEC-S40", event_type="DECISION_RECORDED", status="RECORDED", metadata={"marker": "S40", "action": "NONE"})
    for store in (jobs, queue, approvals, operator, memory, audit):
        store.close()


def sqlite_row_count(path: Path, table: str) -> int:
    import sqlite3
    conn = sqlite3.connect(path)
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        conn.close()


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="ai_os_s40_") as td:
            root = Path(td)
            source = root / "source"
            backup = root / "backup"
            restored = root / "restored"
            source.mkdir()
            seed_state(source)
            original_counts = {
                "jobs": sqlite_row_count(source / "jobs.sqlite3", "jobs"),
                "queue": sqlite_row_count(source / "queue.sqlite3", "queue_jobs"),
                "approvals": sqlite_row_count(source / "approvals.sqlite3", "approvals"),
                "operator": sqlite_row_count(source / "operator.sqlite3", "operator_actions"),
                "memory": sqlite_row_count(source / "memory.sqlite3", "counterfactual_predictions"),
                "audit_traces": sqlite_row_count(source / "audit.sqlite3", "execution_observability_traces"),
                "audit_events": sqlite_row_count(source / "audit.sqlite3", "execution_observability_events"),
            }
            records = backup_sqlite_files(source, backup, NAMES)
            CHECKS["backup_all_state_domains"] = len(records) == len(NAMES)
            CHECKS["backup_manifest_present"] = (backup / "manifest.json").is_file()
            # Simulate destructive loss of the state set.
            shutil.rmtree(source)
            source.mkdir()
            report = restore_sqlite_files(backup, restored, NAMES)
            CHECKS["restore_all_files"] = report.files_present and len(report.restored) == len(NAMES)
            CHECKS["restore_hash_integrity"] = report.hashes_match
            restored_counts = {
                "jobs": sqlite_row_count(restored / "jobs.sqlite3", "jobs"),
                "queue": sqlite_row_count(restored / "queue.sqlite3", "queue_jobs"),
                "approvals": sqlite_row_count(restored / "approvals.sqlite3", "approvals"),
                "operator": sqlite_row_count(restored / "operator.sqlite3", "operator_actions"),
                "memory": sqlite_row_count(restored / "memory.sqlite3", "counterfactual_predictions"),
                "audit_traces": sqlite_row_count(restored / "audit.sqlite3", "execution_observability_traces"),
                "audit_events": sqlite_row_count(restored / "audit.sqlite3", "execution_observability_events"),
            }
            CHECKS["restored_state_readable"] = all(v >= 1 for v in restored_counts.values())
            CHECKS["row_count_integrity"] = restored_counts == original_counts

        p = subprocess.run([sys.executable, str(ROOT / "tests" / "test_s40_state_recovery.py")], cwd=ROOT, text=True, capture_output=True, timeout=45)
        CHECKS["targeted_tests"] = p.returncode == 0 and "S40_TARGETED_TESTS_PASS 6/6" in (p.stdout + p.stderr)
        test_output = (p.stdout + p.stderr).strip()
        compile_p = subprocess.run([sys.executable, "-m", "compileall", "-q", "src"], cwd=ROOT, text=True, capture_output=True, timeout=45)
        CHECKS["compileall"] = compile_p.returncode == 0
    except Exception as exc:
        NOTES.append(type(exc).__name__ + ": " + str(exc)[:240])
        test_output = ""
        CHECKS.setdefault("targeted_tests", False)
        CHECKS.setdefault("compileall", False)

    status = "PASS" if CHECKS and all(CHECKS.values()) else "FAIL"
    report = {
        "release": "O39-S40",
        "status": status,
        "checks": CHECKS,
        "state_domains": NAMES,
        "targeted_test_output": test_output,
        "external_action_executed": False,
        "memory_write_executed": False,
        "internet_facing_production_approval": False,
        "notes": NOTES,
    }
    out = ROOT / "staging"
    out.mkdir(exist_ok=True)
    (out / "s40_state_recovery.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("S40_STATE_RECOVERY_" + status)
    print(json.dumps(report, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
