from typing import Dict, Any


def validate_hardening(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    issues=[]

    if snapshot.get("unknown_action_default") != "DENY":
        issues.append({"type":"policy_default_not_deny"})

    if snapshot.get("secrets_plaintext_persisted") is not False:
        issues.append({"type":"secret_persistence_risk"})

    if snapshot.get("approval_required_for_consequential") is not True:
        issues.append({"type":"missing_consequential_approval"})

    if snapshot.get("rate_limit_enabled") is not True:
        issues.append({"type":"missing_rate_limit"})

    if snapshot.get("circuit_breaker_enabled") is not True:
        issues.append({"type":"missing_circuit_breaker"})

    return {
        "qa_id":"O25-SECURITY-QA",
        "status":"PASS" if not issues else "FAIL",
        "issues":issues,
    }
