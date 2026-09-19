from typing import Dict, Any, List

class FunnelAnalyzer:
    def analyze(self, events: List[Dict[str, Any]], stages: List[str]) -> Dict[str, Any]:
        counts = {s: sum(1 for e in events if e["event_type"] == s) for s in stages}
        transitions = []
        for i in range(len(stages) - 1):
            a, b = counts[stages[i]], counts[stages[i + 1]]
            transitions.append({
                "from": stages[i],
                "to": stages[i + 1],
                "from_count": a,
                "to_count": b,
                "conversion_rate": b / a if a else 0.0,
            })
        return {
            "stage_counts": counts,
            "transitions": transitions,
            "bottleneck": min(transitions, key=lambda x: x["conversion_rate"]) if transitions else None,
        }
