from __future__ import annotations

from src.bounded_self_optimization import BoundedSelfOptimizer
from src.optimization_store import OptimizationStore


def main() -> None:
    proposal = BoundedSelfOptimizer.propose(
        project_id="V08-SMOKE",
        proposal={
            "component": "routing",
            "change_type": "ROUTING",
            "current_value": "route-A",
            "proposed_value": "route-B",
            "rationale": "smoke-test bounded optimization",
            "evidence_refs": ["SMOKE-EVIDENCE"],
            "rollback_plan": "restore route-A",
            "risk_class": "LOW",
            "apply_mode": "GOVERNED_APPLY",
        },
    )
    simulation = BoundedSelfOptimizer.simulate(
        proposal,
        baseline={"quality": 0.70, "latency": 100},
        simulated={"quality": 0.86, "latency": 95},
        sample_count=10,
        uncertainty={"uncertainty_band": "LOW", "reliability_band": "STRONG"},
    )
    evaluation = BoundedSelfOptimizer.evaluate(proposal, simulation, success_metrics=["quality"], minimum_improvement=0.10)
    governance = BoundedSelfOptimizer.govern(proposal, evaluation)

    assert proposal["status"] == "PROPOSED"
    assert simulation["status"] == "SIMULATED"
    assert simulation["production_state_changed"] is False
    assert evaluation["decision"] == "GO"
    assert governance["decision"] == "REVIEW"

    store = OptimizationStore(":memory:")
    try:
        store.create(proposal["change_id"], "V08-SMOKE", proposal["proposal"])
        store.update_status(proposal["change_id"], "EVALUATED", evaluation=evaluation, governance=governance)
        stored = store.get(proposal["change_id"])
        assert stored["status"] == "EVALUATED"
    finally:
        store.close()

    print("V0.8 BOUNDED SELF-OPTIMIZATION SMOKE PASS")
    print({
        "change_id": proposal["change_id"],
        "simulation": simulation["status"],
        "evaluation": evaluation["decision"],
        "governance": governance["decision"],
        "external_action_executed": False,
        "rollback_required": True,
        "governance_authority": governance["governance_authority"],
    })


if __name__ == "__main__":
    main()
