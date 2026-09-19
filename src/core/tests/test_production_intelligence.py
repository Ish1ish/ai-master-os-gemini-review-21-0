import unittest

from src.production_intelligence import ProductionIntelligence
from src.production_intelligence_store import ProductionIntelligenceStore


class TestProductionIntelligence(unittest.TestCase):
    def observation(self, **overrides):
        payload = {
            "provider": "provider-A",
            "tool": "search",
            "observed_at": "2026-09-12T00:00:00Z",
            "cost_usd": 0.02,
            "latency_ms": 120,
            "success_rate": 0.995,
            "sample_count": 100,
            "cpu_pct": 50,
            "memory_pct": 60,
            "freshness": "FRESH",
            "evidence_refs": ["OPS-1"],
        }
        payload.update(overrides)
        return payload

    def test_normalize_observation(self):
        out = ProductionIntelligence.normalize_observation(self.observation())
        self.assertEqual(out["status"], "NORMALIZED")
        self.assertEqual(out["reliability_band"], "STRONG")

    def test_invalid_metrics_fail_closed(self):
        out = ProductionIntelligence.normalize_observation(self.observation(success_rate=1.5))
        self.assertEqual(out["status"], "REJECTED")
        self.assertIn("success_rate_out_of_range", out["reasons"])

    def test_missing_telemetry_is_unknown(self):
        out = ProductionIntelligence.normalize_observation(self.observation(cost_usd=None, latency_ms=None, success_rate=None, sample_count=0, cpu_pct=None, memory_pct=None))
        self.assertEqual(out["reliability_band"], "UNKNOWN")

    def test_reliability_requires_sufficient_history(self):
        self.assertEqual(ProductionIntelligence.reliability_band(success_rate=0.999, sample_count=1), "WEAK")
        self.assertEqual(ProductionIntelligence.reliability_band(success_rate=0.999, sample_count=100), "STRONG")

    def test_resource_pressure_escalates(self):
        self.assertEqual(ProductionIntelligence.resource_pressure(cpu_pct=90, memory_pct=40)["band"], "ELEVATED")
        self.assertEqual(ProductionIntelligence.resource_pressure(cpu_pct=98, memory_pct=40)["band"], "CRITICAL")

    def test_assessment_detects_latency_and_cost_pressure(self):
        out = ProductionIntelligence.assess([self.observation(cost_usd=0.20, latency_ms=500)], max_latency_ms=300, max_cost_usd=0.10)
        self.assertEqual(out["latency_posture"], "SLOW")
        self.assertEqual(out["cost_posture"], "OVER_BUDGET")

    def test_assessment_handles_rejected_observation(self):
        out = ProductionIntelligence.assess([self.observation(success_rate=2.0)], max_latency_ms=300, max_cost_usd=0.10)
        self.assertEqual(out["observation_count"], 0)
        self.assertEqual(out["rejected_count"], 1)
        self.assertEqual(out["latency_posture"], "UNKNOWN")

    def test_recommendation_is_deterministic(self):
        assessment = ProductionIntelligence.assess([self.observation()], max_latency_ms=300, max_cost_usd=0.10)
        candidates = [
            {"provider": "B", "tool": "search", "cost_usd": 0.03, "latency_ms": 100, "success_rate": 0.99},
            {"provider": "A", "tool": "search", "cost_usd": 0.02, "latency_ms": 120, "success_rate": 0.995},
        ]
        context = {"risk_class": "LOW", "project": "P1"}
        a = ProductionIntelligence.recommend(project_id="P1", context=context, assessment=assessment, candidates=candidates)
        b = ProductionIntelligence.recommend(project_id="P1", context=context, assessment=assessment, candidates=candidates)
        self.assertEqual(a["recommendation_id"], b["recommendation_id"])
        self.assertFalse(a["external_action_executed"])

    def test_resource_pressure_raises_caution(self):
        assessment = ProductionIntelligence.assess([self.observation(cpu_pct=92)], max_latency_ms=300, max_cost_usd=0.10)
        out = ProductionIntelligence.recommend(project_id="P1", context={}, assessment=assessment, candidates=[{"provider": "A", "tool": "search", "cost_usd": 0.02, "latency_ms": 100, "success_rate": 0.99}])
        self.assertEqual(out["caution"], "ELEVATED")

    def test_unknown_candidates_hold(self):
        assessment = ProductionIntelligence.assess([], max_latency_ms=300, max_cost_usd=0.10)
        out = ProductionIntelligence.recommend(project_id="P1", context={}, assessment=assessment, candidates=[])
        self.assertEqual(out["action"], "HOLD_AND_COLLECT_TELEMETRY")
        self.assertTrue(out["requires_governance"])

    def test_store_is_idempotent(self):
        store = ProductionIntelligenceStore(":memory:")
        try:
            p = self.observation()
            a = store.create("OBS-1", "P1", p)
            b = store.create("OBS-1", "P1", p)
            self.assertEqual(a["observation_id"], b["observation_id"])
            self.assertEqual(len(store.list("P1")), 1)
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
