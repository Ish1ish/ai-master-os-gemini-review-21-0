from typing import Callable, Dict, Any, List, Optional
from .search_provider import SearchProvider
from .research_planner import ResearchPlanner
from .evidence import build_evidence_pack
from .analyzer import MarketAnalyzer
from .qa import validate_report


class RealMarketIntelligenceEngine:
    def __init__(self, search_provider: Optional[Callable[[str], Dict[str, Any]]] = None):
        self.search = SearchProvider(search_provider)
        self.planner = ResearchPlanner()
        self.analyzer = MarketAnalyzer()

    def research(self, request: str, goal: str = "",
                 dimensions: List[str] | None = None) -> Dict[str, Any]:
        plan = self.planner.build_queries(request, goal, dimensions)
        search_payloads = []

        for dim, query in plan["queries"].items():
            payload = self.search.search(query)
            if payload["status"] != "SUCCESS":
                return {
                    "status": "RESEARCH_UNAVAILABLE",
                    "engine_id": "E-02",
                    "engine_version": "O11-v1.0",
                    "plan": plan,
                    "reason": payload["reason"],
                    "blocked_at": dim,
                }
            search_payloads.append({
                "dimension": dim,
                "query": query,
                "results": payload.get("results", []),
            })

        evidence_pack = build_evidence_pack(search_payloads)
        report = self.analyzer.analyze(request, plan, evidence_pack)
        qa = validate_report(report)

        return {
            "status": "COMPLETE" if qa["status"] == "PASS" else "FAILED",
            "engine_id": "E-02",
            "engine_version": "O11-v1.0",
            "plan": plan,
            "searches": search_payloads,
            "evidence": evidence_pack,
            "report": report,
            "qa": qa,
        }
