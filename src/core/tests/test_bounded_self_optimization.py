import unittest

from src.bounded_self_optimization import BoundedSelfOptimizer
from src.optimization_store import OptimizationStore


class TestBoundedSelfOptimization(unittest.TestCase):
    def base_proposal(self, **overrides):
        payload = {
            "component": "routing",
            "change_type": "ROUTING",
            "current_value": "route-A",
            "proposed_value": "route-B",
            "rationale": "bounded simulated improvement",
            "evidence_refs": ["SIM-E1", "CAL-E2"],
            "rollback_plan": "restore route-A",
            "risk_class": "LOW",
            "apply_mode": "GOVERNED_APPLY",
        }
        payload.update(overrides)
        return payload

    def test_change_id_is_deterministic(self):
        p = self.base_proposal()
        self.assertEqual(BoundedSelfOptimizer.change_id("P1", p), BoundedSelfOptimizer.change_id("P1", p))

    def test_proposal_requires_rollback_and_evidence(self):
        out = BoundedSelfOptimizer.propose(project_id="P1", proposal=self.base_proposal(evidence_refs=[], rollback_plan=""))
        self.assertEqual(out["status"], "REJECTED")
        self.assertIn("evidence_refs_required", out["reasons"])
        self.assertIn("rollback_plan_required", out["reasons"])

    def test_simulation_is_side_effect_free(self):
        p = BoundedSelfOptimizer.propose(project_id="P1", proposal=self.base_proposal())
        sim = BoundedSelfOptimizer.simulate(p, baseline={"quality": 0.70, "latency": 100}, simulated={"quality": 0.85, "latency": 95}, sample_count=0)
        self.assertEqual(sim["status"], "SIMULATED")
        self.assertEqual(sim["production_state_changed"], False)
        self.assertEqual(sim["side_effects"], "NONE")
        self.assertEqual(sim["metric_delta"]["quality"], 0.15)

    def test_high_uncertainty_forces_refine(self):
        p = BoundedSelfOptimizer.propose(project_id="P1", proposal=self.base_proposal())
        sim = BoundedSelfOptimizer.simulate(p, baseline={"quality": 0.70}, simulated={"quality": 0.90}, sample_count=1)
        evaluation = BoundedSelfOptimizer.evaluate(p, sim, success_metrics=["quality"], minimum_improvement=0.05)
        self.assertEqual(evaluation["decision"], "REFINE")

    def test_governance_keeps_consequential_changes_under_review(self):
        p = BoundedSelfOptimizer.propose(project_id="P1", proposal=self.base_proposal(financial=True))
        sim = BoundedSelfOptimizer.simulate(p, baseline={"quality": 0.7}, simulated={"quality": 0.9}, sample_count=10, uncertainty={"uncertainty_band": "LOW"})
        ev = BoundedSelfOptimizer.evaluate(p, sim, success_metrics=["quality"], minimum_improvement=0.1)
        gov = BoundedSelfOptimizer.govern(p, ev)
        self.assertEqual(ev["decision"], "GO")
        self.assertEqual(gov["decision"], "REVIEW")
        self.assertIn("financial", gov["consequential_flags"])

    def test_simulation_only_never_applies(self):
        p = BoundedSelfOptimizer.propose(project_id="P1", proposal=self.base_proposal(apply_mode="SIMULATION_ONLY"))
        sim = BoundedSelfOptimizer.simulate(p, baseline={"quality": 0.7}, simulated={"quality": 0.9}, sample_count=10, uncertainty={"uncertainty_band": "LOW"})
        ev = BoundedSelfOptimizer.evaluate(p, sim, success_metrics=["quality"], minimum_improvement=0.1)
        gov = BoundedSelfOptimizer.govern(p, ev)
        out = BoundedSelfOptimizer.apply(p, ev, gov, approved=True, version="v2", previous_version="v1")
        self.assertEqual(gov["decision"], "SIMULATION_ONLY")
        self.assertEqual(out["status"], "REJECTED")
        self.assertIn("simulation_only", out["reason"])

    def test_apply_requires_explicit_approval_and_versions(self):
        p = BoundedSelfOptimizer.propose(project_id="P1", proposal=self.base_proposal())
        sim = BoundedSelfOptimizer.simulate(p, baseline={"quality": 0.7}, simulated={"quality": 0.9}, sample_count=10, uncertainty={"uncertainty_band": "LOW"})
        ev = BoundedSelfOptimizer.evaluate(p, sim, success_metrics=["quality"], minimum_improvement=0.1)
        gov = BoundedSelfOptimizer.govern(p, ev)
        denied = BoundedSelfOptimizer.apply(p, ev, gov, approved=False, version="v2", previous_version="v1")
        self.assertEqual(denied["reason"], "explicit_approval_required")
        applied = BoundedSelfOptimizer.apply(p, ev, gov, approved=True, version="v2", previous_version="v1")
        self.assertEqual(applied["status"], "APPLIED")
        self.assertEqual(applied["external_action_executed"], False)

    def test_rollback_is_reversible(self):
        out = BoundedSelfOptimizer.rollback({"status": "APPLIED", "change_id": "OPT-1", "previous_version": "v1"})
        self.assertEqual(out["status"], "ROLLED_BACK")
        self.assertEqual(out["restored_version"], "v1")

    def test_store_is_idempotent(self):
        store = OptimizationStore(":memory:")
        try:
            payload = {"component": "routing", "change_type": "ROUTING"}
            a = store.create("OPT-1", "P1", payload)
            b = store.create("OPT-1", "P1", payload)
            self.assertEqual(a["change_id"], b["change_id"])
            self.assertEqual(store.get("OPT-1")["status"], "PROPOSED")
            store.update_status("OPT-1", "SIMULATED", evaluation={"decision": "REFINE"})
            self.assertEqual(store.get("OPT-1")["status"], "SIMULATED")
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
