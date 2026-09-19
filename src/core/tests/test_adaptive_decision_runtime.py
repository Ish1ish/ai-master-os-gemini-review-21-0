import unittest

from src.adaptive_decision_context_store import AdaptiveDecisionContextStore
from src.adaptive_decision_runtime import AdaptiveDecisionRuntime


class TestAdaptiveDecisionRuntime(unittest.TestCase):
    def analysis(self):
        return {
            "analysis_id": "AOA-123",
            "project_id": "P1",
            "analysis_status": "ANALYZED",
            "advisory_route": "REFINE_DECISION",
            "findings": ["REPEATED_DECISION_MISSES"],
            "sample_size": 6,
            "confidence": "medium",
        }

    def test_runtime_builds_and_persists(self):
        store = AdaptiveDecisionContextStore(":memory:")
        runtime = AdaptiveDecisionRuntime(store)
        result = runtime.build_context(
            "P1",
            analysis=self.analysis(),
            candidate_decision="RECOMMEND",
        )
        self.assertEqual(result["context"]["advisory_decision"], "REFINE")
        self.assertEqual(result["persistence"]["status"], "RECORDED")
        self.assertTrue(result["governance_unchanged"])
        self.assertFalse(result["external_action_executed"])
        self.assertFalse(result["o43_memory_mutated"])
        store.close()

    def test_runtime_replay_is_idempotent(self):
        store = AdaptiveDecisionContextStore(":memory:")
        runtime = AdaptiveDecisionRuntime(store)
        first = runtime.build_context("P1", analysis=self.analysis(), candidate_decision="RECOMMEND")
        second = runtime.build_context("P1", analysis=self.analysis(), candidate_decision="RECOMMEND")
        self.assertEqual(first["context"]["context_id"], second["context"]["context_id"])
        self.assertEqual(second["persistence"]["status"], "IDEMPOTENT_REPLAY")
        store.close()


if __name__ == "__main__":
    unittest.main()
