from typing import Any, Dict, List


def qa_knowledge_aware_run(user_text: str, knowledge_pack: Dict[str, Any],
                           provenance: Dict[str, Any], freshness: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    checks.append({
        "check": "knowledge_attached",
        "status": "PASS" if knowledge_pack.get("knowledge_ids") else "FAIL",
        "details": knowledge_pack.get("knowledge_ids", [])
    })
    checks.append({
        "check": "provenance_bound",
        "status": "PASS" if provenance.get("bindings") else "FAIL",
        "details": provenance.get("source_refs", [])
    })
    if freshness["status"] == "REFRESH_REQUIRED":
        checks.append({
            "check": "freshness",
            "status": "WARN",
            "details": freshness["message"]
        })
    else:
        checks.append({
            "check": "freshness",
            "status": "PASS",
            "details": freshness["message"]
        })

    status = "PASS" if all(c["status"] in {"PASS", "WARN"} for c in checks) else "FAIL"
    return {
        "qa_id": "O3-QA-001",
        "status": status,
        "checks": checks,
        "warnings": [c["details"] for c in checks if c["status"] == "WARN"],
    }
