from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "src")

from core.src.approval_store import ApprovalStore
from core.src.execution_observability import ExecutionObservabilityStore
from core.src.jobs import JobStore
from core.src.decision_memory import CounterfactualDecisionMemory
from core.src.operator_store import OperatorStore
from core.src.queue import DurableQueue
from core.src.state_recovery import backup_sqlite_files, restore_sqlite_files, sha256_file


def make_fixture(root: Path):
    names = [
        "jobs.sqlite3",
        "queue.sqlite3",
        "approvals.sqlite3",
        "operator.sqlite3",
        "memory.sqlite3",
        "audit.sqlite3",
    ]
    jobs = JobStore(str(root / names[0]))
    jobs.create("JOB-S40", "PROJ-S40", "backup restore drill", language="en")
    jobs.set_status("JOB-S40", "COMPLETE", result={"marker": "S40"})

    queue = DurableQueue(str(root / names[1]))
    queue.enqueue("JOB-S40", {"marker": "S40"})
    queue.complete("JOB-S40", {"queue": "COMPLETE"})

    approvals = ApprovalStore(str(root / names[2]))
    approval = approvals.create("JOB-S40", "publish_public_content", {"marker": "S40"}, requested_by="operator-01")
    approvals.decide(approval["approval_id"], "REJECTED", "operator-01", "drill only")

    operator = OperatorStore(str(root / names[3]))
    operator.record("operator-01", "backup_drill", "JOB-S40", {"marker": "S40"})

    memory = CounterfactualDecisionMemory(str(root / names[4]))
    pred = memory.record_prediction(
        project_id="PROJ-S40",
        requested_by="operator-01",
        prediction={"plan_hash": "S40-PLAN", "decision": "REVIEW", "risk": "LOW", "actions": [], "side_effects": "NONE"},
    )
    memory.observe_outcome(prediction_id=pred["prediction_id"], actual={"decision": "REVIEW", "risk": "LOW"})

    audit = ExecutionObservabilityStore(str(root / names[5]))
    audit.record_event(project_id="PROJ-S40", run_id="JOB-S40", decision_plan_id="PLAN-S40", intent_id="INTENT-S40", execution_id="EXEC-S40", event_type="DECISION_RECORDED", status="RECORDED", metadata={"marker": "S40", "action": "NONE"})

    for store in (jobs, queue, approvals, operator, memory, audit):
        store.close()
    return names


def test_fixture_contains_expected_state():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        names = make_fixture(root)
        assert all((root / name).is_file() for name in names)
        assert all(sha256_file(root / name) for name in names)


def test_backup_creates_manifest_and_all_files():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); names = make_fixture(root)
        records = backup_sqlite_files(root, root / "backup", names)
        manifest = json.loads((root / "backup" / "manifest.json").read_text(encoding="utf-8"))
        assert len(records) == len(names)
        assert len(manifest["records"]) == len(names)
        assert all((root / "backup" / name).is_file() for name in names)


def test_restore_reproduces_exact_hashes():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); names = make_fixture(root)
        original = {name: sha256_file(root / name) for name in names}
        backup_sqlite_files(root, root / "backup", names)
        report = restore_sqlite_files(root / "backup", root / "restored", names)
        restored = {name: sha256_file(root / "restored" / name) for name in names}
        assert report.files_present and report.hashes_match
        assert restored == original


def test_restored_state_is_readable():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); names = make_fixture(root)
        backup_sqlite_files(root, root / "backup", names)
        restore_sqlite_files(root / "backup", root / "restored", names)
        conn = sqlite3.connect(root / "restored" / "jobs.sqlite3")
        job = conn.execute("SELECT job_id,status FROM jobs WHERE job_id='JOB-S40'").fetchone()
        conn.close()
        assert job == ("JOB-S40", "COMPLETE")


def test_manifest_is_self_contained_and_secret_safe():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); names = make_fixture(root)
        backup_sqlite_files(root, root / "backup", names)
        text = (root / "backup" / "manifest.json").read_text(encoding="utf-8").lower()
        assert "api_key" not in text
        assert "authorization" not in text
        assert "secret" not in text


def test_restore_is_idempotent():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); names = make_fixture(root)
        backup_sqlite_files(root, root / "backup", names)
        first = restore_sqlite_files(root / "backup", root / "restored", names)
        second = restore_sqlite_files(root / "backup", root / "restored", names)
        assert first.hashes_match and second.hashes_match
        assert first.restored == second.restored == names


if __name__ == "__main__":
    tests = [
        test_fixture_contains_expected_state,
        test_backup_creates_manifest_and_all_files,
        test_restore_reproduces_exact_hashes,
        test_restored_state_is_readable,
        test_manifest_is_self_contained_and_secret_safe,
        test_restore_is_idempotent,
    ]
    for test in tests:
        test()
    print(f"S40_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")
