from typing import Dict, Any

class ExperimentAnalyzer:
    def compare(self, experiment_name: str, control: Dict[str, Any],
                variant: Dict[str, Any], metric: str, higher_is_better: bool = True) -> Dict[str, Any]:
        c = float(control.get(metric, 0))
        v = float(variant.get(metric, 0))
        delta = v - c
        winner = ("variant" if v > c else "control" if c > v else "tie") if higher_is_better else                  ("variant" if v < c else "control" if c < v else "tie")
        return {
            "experiment": experiment_name,
            "metric": metric,
            "control": c,
            "variant": v,
            "absolute_delta": delta,
            "relative_delta": (delta / c if c else None),
            "winner_by_observed_metric": winner,
            "causality_claim_allowed": False,
            "note": "Observed difference alone is not proof of significance or causal effect.",
        }
