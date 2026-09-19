from typing import Dict, Any

HIGH_IMPACT_ACTIONS = {
    "publish_public_content",
    "send_external_message",
    "change_ad_budget",
    "change_price",
    "payment_or_refund",
    "modify_or_delete_data",
    "activate_integration",
    "autonomous_external_agent_action",
}

def classify_risk(action: str, external_effect: bool=False, financial: bool=False,
                  destructive: bool=False) -> str:
    if destructive or financial:
        return "critical"
    if action in HIGH_IMPACT_ACTIONS or external_effect:
        return "high"
    return "low"

def requires_approval(risk: str) -> bool:
    return risk in {"high","critical"}

def build_risk_context(action: str, risk: str, flags: Dict[str, Any]) -> Dict[str, Any]:
    return {"action": action, "risk": risk, "flags": flags}
