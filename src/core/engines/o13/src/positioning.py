from src.handoff_contracts import semantic_core, compact_semantic_text

def build_positioning(idea, market_report=None):
    market_report = market_report or {}
    proof_points=[]
    for f in market_report.get("findings",[])[:5]:
        if f.get("statement") and f.get("source_id"):
            proof_points.append({"statement":compact_semantic_text(f["statement"]),"source_id":f["source_id"]})
    problem = semantic_core(idea.get("problem_statement") or idea.get("evidence_summary") or idea.get("idea") or "validated customer problem")
    customer = semantic_core(idea.get("customer_segment") or idea.get("audience") or "defined audience")
    outcome = semantic_core(idea.get("desired_outcome") or "a useful customer outcome")
    title = semantic_core(idea.get("title") or "focused solution")
    return {
        "target_problem":problem,
        "positioning_direction":f"{title} for {customer}: address {problem} with a simpler path to {outcome}.",
        "differentiation_hypothesis":f"Win through sharper focus on {customer}, a simpler onboarding path, and a clearly defined outcome: {outcome}.",
        "proof_points":proof_points,
        "boundary":"Positioning is a strategic hypothesis until validated with real customers and competitors.",
    }
