from typing import Dict, Any, List

class BottleneckDiagnoser:
    def diagnose(self, funnel_analysis: Dict[str, Any], experiment_results: List[Dict[str, Any]] | None = None):
        recs = []
        bottleneck = funnel_analysis.get("bottleneck")
        if bottleneck:
            recs.append({
                "priority": "HIGH",
                "area": f"{bottleneck['from']} → {bottleneck['to']}",
                "reason": "Lowest observed transition rate in the supplied funnel.",
                "next_test": "Test the first major variable controlling this transition.",
            })
        for exp in experiment_results or []:
            if exp.get("winner_by_observed_metric") == "variant":
                recs.append({
                    "priority": "MEDIUM",
                    "area": exp["experiment"],
                    "reason": "Variant had a higher observed metric.",
                    "next_test": "Replicate with appropriate sample and controlled design.",
                })
        if not recs:
            recs.append({
                "priority":"LOW",
                "area":"Measurement",
                "reason":"No clear bottleneck detected from supplied data.",
                "next_test":"Improve instrumentation and run a focused baseline.",
            })
        return {"primary_bottleneck": bottleneck, "recommendations": recs}
