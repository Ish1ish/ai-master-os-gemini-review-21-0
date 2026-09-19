from typing import Dict, Any, List

RESEARCH_DIMENSIONS = [
    "customer_problem", "desired_outcome", "market_demand", "competitor_landscape",
    "offer_gaps", "pricing_context", "distribution_channels", "current_trends",
]
EGYPT_LOCAL_CONTEXT = (
    "Egypt Egyptian SMEs small businesses Cairo Giza Alexandria local competitors local offers "
    "local pricing EGP WhatsApp Arabic reviews complaints alternatives"
)
LOCAL_SEGMENT_QUERIES = [
    "Egypt small retail shops",
    "Egypt restaurants cafes",
    "Egypt salons barbers",
    "Egypt ecommerce social commerce sellers",
    "Egypt freelancers professional services",
    "Egypt auto repair workshops",
    "Egypt real estate agents",
    "Egypt clinics dental clinics",
    "Egypt tutoring language schools",
    "Egypt logistics delivery businesses",
]

class ResearchPlanner:
    def build_queries(self, request: str, goal: str = "", dimensions: List[str] | None = None) -> Dict[str, Any]:
        dims = dimensions or RESEARCH_DIMENSIONS[:]
        # Keep the user's intent compact; repeating the entire request across every query
        # made search engines over-index on generic "AI business ideas" content.
        intent = "low-cost AI business opportunity for Egyptian small businesses and entrepreneurs"
        query_map = {}
        for dim in dims:
            if dim == "customer_problem":
                q = f"Egypt customer complaints recurring problems {intent} reviews pain points WhatsApp"
            elif dim == "desired_outcome":
                q = f"Egypt small business customer needs desired outcomes jobs to be done {intent}"
            elif dim == "market_demand":
                q = f"Egypt SME demand signals AI automation software adoption customer intent {intent}"
            elif dim == "competitor_landscape":
                q = f"Egypt local competitors alternatives AI automation agencies SaaS freelancers SME pricing"
            elif dim == "offer_gaps":
                q = f"Egypt underserved SME workflows gaps WhatsApp Arabic local support alternatives {intent}"
            elif dim == "pricing_context":
                q = f"Egypt EGP pricing offers packages subscriptions AI automation SME competitors"
            elif dim == "distribution_channels":
                q = f"Egypt SME customer acquisition channels WhatsApp Facebook Instagram search communities"
            elif dim == "current_trends":
                q = f"Egypt 2025 2026 SME AI adoption automation digital business trends official report"
            else:
                q = f"Egypt {dim.replace('_',' ')} {intent}"
            query_map[dim] = q

        segment_scans = []
        for segment in LOCAL_SEGMENT_QUERIES:
            segment_scans.append(
                f"{segment} customer complaints reviews pain points manual workflow problems AI automation"
            )
        query_map["local_problem_scan"] = " | ".join(segment_scans)
        query_map["local_competitor_scan"] = (
            "Egypt local competitor search: AI agency OR WhatsApp automation OR CRM OR POS OR accounting "
            "OR social media management OR workflow automation; include pricing EGP where public"
        )

        return {
            "base_request": request,
            "goal": goal,
            "dimensions": list(query_map.keys()),
            "queries": query_map,
            "research_policy": {
                "country_priority": "Egypt-first",
                "local_evidence_required": True,
                "global_sources_role": "secondary_context_only",
                "preferred_signal_types": [
                    "customer_language", "complaints", "reviews", "local_competitors",
                    "local_pricing", "local_alternatives", "official_or_industry_reports",
                ],
                "rejection_signals": [
                    "generic idea lists", "AI idea generators", "global startup listicles",
                    "vendor self-claims without local relevance",
                ],
            },
        }
