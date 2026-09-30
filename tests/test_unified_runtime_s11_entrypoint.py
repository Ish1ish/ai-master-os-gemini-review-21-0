import tempfile
import unittest

from unified_runtime.entrypoint import UnifiedRuntimeEntrypoint, UnifiedRuntimeRequest


class TestS11UnifiedRuntimeEntrypoint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.entrypoint = UnifiedRuntimeEntrypoint(self.tmp.name)

    def tearDown(self):
        self.entrypoint.close()
        self.tmp.cleanup()

    def _payload(self, **overrides):
        payload = {
            "run_id": "UR-S11-001",
            "project_id": "demo",
            "strategy_id": "STRAT-A",
            "intent": "Validate a low-cost AI workflow",
            "goal": "Prove a bounded next step",
            "audience": "Egypt SMB founders",
        }
        payload.update(overrides)
        return payload

    def test_mapping_request_reaches_real_runtime(self):
        result = self.entrypoint.run(self._payload())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["stage_count"], 13)
        self.assertEqual(result["runtime_mode"], "REAL_ADAPTER_WIRING")
        self.assertEqual(result["entrypoint"]["request_mode"], "UNIFIED_RUNTIME_ENTRYPOINT")

    def test_dataclass_request_is_supported(self):
        request = UnifiedRuntimeRequest.from_mapping(self._payload(run_id="UR-S11-002"))
        result = self.entrypoint.run(request)
        self.assertEqual(result["run_id"], "UR-S11-002")
        self.assertEqual(result["project_id"], "demo")

    def test_required_fields_fail_closed(self):
        result = self.entrypoint.run({"project_id": "demo", "intent": "missing identity"})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("missing_required_fields", result["reason"])
        self.assertFalse(result["external_action"])
        self.assertFalse(result["memory_write"])

    def test_invalid_constraints_fail_closed(self):
        result = self.entrypoint.run(self._payload(constraints=["not", "a", "mapping"]))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "constraints_must_be_mapping")

    def test_invalid_evidence_fail_closed(self):
        result = self.entrypoint.run(self._payload(evidence=["not", "a", "mapping"]))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "evidence_must_be_mapping")

    def test_safety_flags_are_explicit(self):
        result = self.entrypoint.run(self._payload())
        self.assertFalse(result["external_action"])
        self.assertFalse(result["governance_mutation"])
        self.assertFalse(result["memory_write"])
        self.assertFalse(result["entrypoint"]["external_action_capability"])

    def test_runtime_failure_fails_closed(self):
        original = self.entrypoint.runtime.run
        self.entrypoint.runtime.run = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            result = self.entrypoint.run(self._payload(run_id="UR-S11-007"))
        finally:
            self.entrypoint.runtime.run = original
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "runtime_error")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertFalse(result["external_action"])
        self.assertFalse(result["memory_write"])

    def test_replay_preserves_identity_and_persistence(self):
        payload = self._payload(run_id="UR-S11-008")
        first = self.entrypoint.run(payload)
        second = self.entrypoint.run(payload)
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual(first["project_id"], second["project_id"])
        self.assertEqual(first["persistence"]["status"], "PERSISTED")
        self.assertEqual(second["persistence"]["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(first["persistence"]["fingerprint"], second["persistence"]["fingerprint"])


if __name__ == "__main__":
    unittest.main()
