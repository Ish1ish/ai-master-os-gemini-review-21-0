import os
import tempfile
import unittest

from src.governance_intelligence import GovernanceIntelligence
from src.o45_execution_service import ExecutionPolicy, ExecutionService
from src.receipt_store import ExecutionReceiptStore
from src.tool_registry import ToolRegistry


class TestO45ExecutionHardening(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.governance = GovernanceIntelligence(os.path.join(self.tmp.name, "governance.sqlite3"))
        self.registry = ToolRegistry()
        self.calls = []

        def handler(payload):
            self.calls.append(dict(payload))
            return {"ok": True, "value": payload.get("value")}

        self.registry.register("test.echo", handler, version="1.0.0")
        self.receipts = ExecutionReceiptStore(os.path.join(self.tmp.name, "executions.sqlite3"))
        self.service = ExecutionService(
            self.governance, self.registry, self.receipts, worker_id="W1", lease_seconds=60
        )

    def tearDown(self):
        self.service.close()
        self.governance.close()
        self.tmp.cleanup()

    def ctx(self, **extra):
        base = {
            "confidence": "high",
            "evidence_refs": ["SRC-1", "SRC-2"],
            "evidence_boundary": "local_evidence_supported",
        }
        base.update(extra)
        return base

    def request(self, **extra):
        data = dict(
            project_id="P1",
            run_id="R1",
            action="read_only_inspection",
            tool_name="test.echo",
            payload={"value": "x"},
            context=self.ctx(),
            idempotency_key="KEY-1",
            requested_by="operator",
        )
        data.update(extra)
        return self.service.request(**data)

    def test_unknown_tool_fails_closed(self):
        out = self.request(tool_name="missing.tool")
        self.assertEqual(out["status"], "BLOCK")
        self.assertEqual(out["reason"], "unknown_tool")

    def test_disabled_tool_fails_closed(self):
        self.registry.disable("test.echo")
        out = self.request()
        self.assertEqual(out["status"], "BLOCK")
        self.assertEqual(out["reason"], "tool_disabled")

    def test_unknown_action_is_blocked_before_handler(self):
        out = self.request(action="does_not_exist", idempotency_key="KEY-2")
        self.assertEqual(out["execution"]["state"], "BLOCKED")
        run = self.service.execute_once(out["execution"]["execution_id"])
        self.assertEqual(run["status"], "BLOCKED")
        self.assertEqual(self.calls, [])

    def test_auto_allow_executes(self):
        out = self.request()
        self.assertEqual(out["execution"]["state"], "READY")
        run = self.service.execute_once(out["execution"]["execution_id"])
        self.assertEqual(run["status"], "SUCCEEDED")
        self.assertEqual(self.calls, [{"value": "x"}])

    def test_same_idempotency_same_request_returns_same_execution(self):
        first = self.request()
        second = self.request()
        self.assertEqual(first["execution"]["execution_id"], second["execution"]["execution_id"])
        self.assertEqual(len(self.receipts.list()), 1)

    def test_same_idempotency_different_request_conflicts(self):
        first = self.request()
        second = self.request(payload={"value": "changed"})
        self.assertEqual(first["status"], "ACCEPTED")
        self.assertEqual(second["status"], "CONFLICT")

    def test_terminal_replay_does_not_execute_again(self):
        out = self.request()
        eid = out["execution"]["execution_id"]
        self.assertEqual(self.service.execute_once(eid)["status"], "SUCCEEDED")
        self.assertEqual(self.service.execute_once(eid)["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(len(self.calls), 1)

    def test_review_waits_for_approval(self):
        out = self.request(
            action="publish_public_content",
            idempotency_key="KEY-3",
        )
        execution = out["execution"]
        self.assertEqual(execution["state"], "AWAITING_APPROVAL")
        self.assertTrue(execution["approval_id"])
        self.assertEqual(
            self.service.execute_once(execution["execution_id"])["status"], "PENDING"
        )

    def test_approval_self_decide_is_denied(self):
        out = self.request(action="publish_public_content", idempotency_key="KEY-4")
        aid = out["execution"]["approval_id"]
        denied = self.governance.decide(
            aid, {"principal_id": "operator", "roles": ["approver"]}, "APPROVED"
        )
        self.assertEqual(denied["status"], "DENY")

    def test_exact_approved_review_becomes_ready(self):
        out = self.request(action="publish_public_content", idempotency_key="KEY-5")
        execution = out["execution"]
        self.governance.decide(
            execution["approval_id"],
            {"principal_id": "approver", "roles": ["approver"]},
            "APPROVED",
            "reviewed",
        )
        ready = self.service.approve_and_ready(execution["execution_id"])
        self.assertEqual(ready["state"], "READY")
        self.assertEqual(self.service.execute_once(ready["execution_id"])["status"], "SUCCEEDED")

    def test_rejected_review_cannot_be_reissued_implicitly(self):
        out = self.request(action="publish_public_content", idempotency_key="KEY-6")
        execution = out["execution"]
        self.governance.decide(
            execution["approval_id"],
            {"principal_id": "approver", "roles": ["approver"]},
            "REJECTED",
            "rejected",
        )
        self.assertEqual(self.service.approve_and_ready(execution["execution_id"])["status"], "BLOCKED")
        self.assertEqual(self.service.execute_once(execution["execution_id"])["status"], "PENDING")

    def test_wrong_approval_action_is_rejected(self):
        out = self.request(action="publish_public_content", idempotency_key="KEY-7")
        execution = out["execution"]
        approval = self.governance.approvals.get(execution["approval_id"])
        approval["action"] = "send_external_message"
        verdict = ExecutionPolicy.validate_approval(
            approval, action="publish_public_content", run_id="R1",
            project_id="P1", approval_id=execution["approval_id"],
        )
        self.assertEqual(verdict["status"], "DENY")
        self.assertEqual(verdict["reason"], "approval_action_mismatch")

    def test_wrong_project_approval_is_rejected(self):
        out = self.request(action="publish_public_content", idempotency_key="KEY-8")
        execution = out["execution"]
        approval = self.governance.approvals.get(execution["approval_id"])
        approval["payload"]["project_id"] = "OTHER"
        verdict = ExecutionPolicy.validate_approval(
            approval, action="publish_public_content", run_id="R1",
            project_id="P1", approval_id=execution["approval_id"],
        )
        self.assertEqual(verdict["status"], "DENY")
        self.assertEqual(verdict["reason"], "approval_project_mismatch")

    def test_worker_claim_is_single_owner(self):
        out = self.request(idempotency_key="KEY-9")
        eid = out["execution"]["execution_id"]
        first = self.receipts.claim(eid, "W1", now_epoch=1000)
        second = self.receipts.claim(eid, "W2", now_epoch=1000)
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_expired_lease_requires_recovery(self):
        out = self.request(idempotency_key="KEY-10")
        eid = out["execution"]["execution_id"]
        self.assertIsNotNone(self.receipts.claim(eid, "W1", lease_seconds=10, now_epoch=1000))
        recovered = self.receipts.recover_expired(now_epoch=1011)
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0]["state"], "RECOVERY_REQUIRED")
        self.assertEqual(self.service.execute_once(eid)["status"], "RECOVERY_REQUIRED")

    def test_handler_exception_is_retryable(self):
        def failing(_):
            raise RuntimeError("temporary")
        self.registry.register("test.fail", failing, version="1.0.0", retry_safe=True)
        out = self.request(tool_name="test.fail", idempotency_key="KEY-11")
        result = self.service.execute_once(out["execution"]["execution_id"])
        self.assertEqual(result["status"], "FAILED_RETRYABLE")
        self.assertEqual(result["execution"]["error"]["type"], "RuntimeError")

    def test_payload_is_not_augmented_with_governance_context(self):
        out = self.request(idempotency_key="KEY-12")
        self.service.execute_once(out["execution"]["execution_id"])
        self.assertEqual(set(self.calls[0].keys()), {"value"})

    def test_approval_request_hash_is_bound(self):
        out = self.request(action="publish_public_content", idempotency_key="KEY-13")
        execution = out["execution"]
        self.governance.decide(
            execution["approval_id"],
            {"principal_id": "approver", "roles": ["approver"]},
            "APPROVED",
            "reviewed",
        )
        approval = self.governance.approvals.get(execution["approval_id"])
        approval["payload"]["o45_request_hash"] = "tampered"
        verdict = ExecutionPolicy.validate_approval(
            approval, action=execution["action"], run_id=execution["run_id"],
            project_id=execution["project_id"], approval_id=execution["approval_id"],
            request_hash=execution["request_hash"],
        )
        self.assertEqual(verdict["status"], "DENY")
        self.assertEqual(verdict["reason"], "approval_request_mismatch")

    def test_execution_audit_events_persist(self):
        out = self.request(idempotency_key="KEY-14")
        eid = out["execution"]["execution_id"]
        self.service.execute_once(eid)
        events = self.service.events(eid)
        self.assertTrue(any(e["event_type"] == "CREATED" for e in events))
        self.assertTrue(any(e["event_type"] == "CLAIMED" for e in events))
        self.assertTrue(any(e["to_state"] == "SUCCEEDED" for e in events))

    def test_non_retry_safe_failure_requires_recovery(self):
        def unsafe_fail(_):
            raise RuntimeError("unknown external outcome")
        self.registry.register("test.unsafe_fail", unsafe_fail, version="1.0.0", retry_safe=False)
        out = self.request(tool_name="test.unsafe_fail", idempotency_key="KEY-15")
        result = self.service.execute_once(out["execution"]["execution_id"])
        self.assertEqual(result["status"], "RECOVERY_REQUIRED")
        self.assertEqual(result["execution"]["state"], "RECOVERY_REQUIRED")

    def test_retry_safe_failure_can_be_requeued_explicitly(self):
        attempts = {"n": 0}
        def flaky(_):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise RuntimeError("temporary")
            return {"ok": True}
        self.registry.register("test.flaky", flaky, version="1.0.0", retry_safe=True)
        out = self.request(tool_name="test.flaky", idempotency_key="KEY-16")
        eid = out["execution"]["execution_id"]
        failed = self.service.execute_once(eid)
        self.assertEqual(failed["status"], "FAILED_RETRYABLE")
        self.assertEqual(self.service.retry(eid)["state"], "READY")
        self.assertEqual(self.service.execute_once(eid)["status"], "SUCCEEDED")


    def test_close_is_idempotent(self):
        self.service.close()
        self.service.close()


if __name__ == "__main__":
    unittest.main()
