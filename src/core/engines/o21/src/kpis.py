from typing import Dict, Any, List

class KPIEngine:
    def funnel_rate(self, events: List[Dict[str, Any]], start_type: str, end_type: str) -> Dict[str, Any]:
        starts = sum(1 for e in events if e["event_type"] == start_type)
        ends = sum(1 for e in events if e["event_type"] == end_type)
        return {
            "metric": f"{end_type}_per_{start_type}",
            "numerator": ends,
            "denominator": starts,
            "rate": ends / starts if starts else 0.0,
        }

    def retention_rate(self, users_started: int, users_retained: int) -> Dict[str, Any]:
        return {
            "metric": "retention_rate",
            "numerator": users_retained,
            "denominator": users_started,
            "rate": users_retained / users_started if users_started else 0.0,
        }

    def revenue_per_customer(self, revenue: float, customers: int) -> Dict[str, Any]:
        return {
            "metric": "revenue_per_customer",
            "revenue": revenue,
            "customers": customers,
            "value": revenue / customers if customers else 0.0,
        }
