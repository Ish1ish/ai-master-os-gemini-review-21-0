from typing import Dict, Any, List


def validate_report(report: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    if not report.get("request"):
        issues.append({"type":"missing_request"})

    if not report.get("research_dimensions"):
        issues.append({"type":"missing_research_dimensions"})

    if report.get("source_count", 0) <= 0:
        issues.append({"type":"no_sources"})

    for finding in report.get("findings", []):
        if finding.get("statement") and not finding.get("source_id"):
            issues.append({
                "type":"unbound_finding",
                "finding_id":finding.get("finding_id")
            })

    return {
        "qa_id":"O11-MARKET-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
        "checks":{
            "request":bool(report.get("request")),
            "dimensions":bool(report.get("research_dimensions")),
            "sources":report.get("source_count",0)>0,
            "findings_bound":not any(x["type"]=="unbound_finding" for x in issues),
        }
    }
