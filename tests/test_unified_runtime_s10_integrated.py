import tempfile
import unittest

from unified_runtime.integrated_runtime import RealUnifiedRuntime


class TestS10RealUnifiedRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = RealUnifiedRuntime(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_runtime_uses_authoritative_engines(self):
        result = self.runtime.run(
            run_id="UR-S10-001",
            project_id="demo",
            strategy_id="STRAT-A",
            intent="Validate a low-cost AI workflow",
            goal="Prove a bounded next step",
            audience="Egypt SMB founders",
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["stage_count"], 13)
        self.assertEqual(result["runtime_mode"], "REAL_ADAPTER_WIRING")
        self.assertEqual(result["decision_engine"], "UnifiedDecisionIntelligence")
        self.assertEqual(result["evidence_engine"], "ValidationEvidenceLoop")

    def test_identity_and_trace_are_host_level(self):
        result = self.runtime.run(
            run_id="UR-S10-002",
            project_id="project-real",
            strategy_id="STRAT-REAL",
            intent="Validate identity propagation",
        )
        self.assertEqual(result["run_id"], "UR-S10-002")
        self.assertEqual(result["project_id"], "project-real")
        self.assertEqual(result["strategy_id"], "STRAT-REAL")
        self.assertEqual({x["run_id"] for x in result["trace"]}, {"UR-S10-002"})

    def test_o42_decision_controls_governance(self):
        result = self.runtime.run(
            run_id="UR-S10-003",
            project_id="demo",
            strategy_id="STRAT-A",
            intent="Validate evidence gates",
            evidence={
                "sample_size": 10,
                "evidence_refs": ["EV-1", "EV-2"],
                "metrics": {"problem_confirmed": 7, "pilot_interest": 1},
            },
        )
        self.assertEqual(result["stages"]["EVALUATION"]["decision"], "REFINE")
        self.assertEqual(result["stages"]["GOVERNANCE"]["posture"], "REFINE_BEFORE_EXECUTION")
        self.assertEqual(result["stages"]["OUTCOME"]["outcome_status"], "BLOCKED")
        self.assertEqual(result["stages"]["ADAPTATION"]["recommendation"], "COLLECT_EVIDENCE")

    def test_no_external_action_or_memory_write(self):
        result = self.runtime.run(
            run_id="UR-S10-004",
            project_id="demo",
            strategy_id="STRAT-A",
            intent="Stay bounded",
        )
        self.assertFalse(result["external_action"])
        self.assertFalse(result["memory_write"])
        self.assertFalse(result["governance_mutation"])
        self.assertFalse(result["memory_proposal"]["memory_write"])
        self.assertTrue(result["memory_proposal"]["human_gate"])

    def test_persistence_and_replay_are_deterministic(self):
        args = dict(
            run_id="UR-S10-005",
            project_id="demo",
            strategy_id="STRAT-A",
            intent="Prove replay",
        )
        first = self.runtime.run(**args)
        second = self.runtime.run(**args)
        self.assertEqual(first["persistence"]["status"], "PERSISTED")
        self.assertEqual(second["persistence"]["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(first["persistence"]["fingerprint"], second["persistence"]["fingerprint"])
        self.assertEqual(first["memory_proposal"], second["memory_proposal"])

    def test_inconclusive_evidence_is_fail_closed(self):
        result = self.runtime.run(
            run_id="UR-S10-006",
            project_id="demo",
            strategy_id="STRAT-A",
            intent="No decision-grade evidence yet",
            evidence={"sample_size": 0, "evidence_refs": [], "metrics": {}},
        )
        self.assertEqual(result["stages"]["EVALUATION"]["decision"], "INCONCLUSIVE")
        self.assertEqual(result["stages"]["GOVERNANCE"]["posture"], "BLOCK")
        self.assertEqual(result["stages"]["OUTCOME"]["outcome_status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
