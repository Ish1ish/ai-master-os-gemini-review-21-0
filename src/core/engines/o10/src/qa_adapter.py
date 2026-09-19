from typing import Dict, Any


def validate_prompt_output(result: Dict[str, Any]) -> Dict[str, Any]:
    prompt = result.get("execution_prompt", {})
    required = ["prompt_text", "techniques_used", "output_format"]
    missing = [k for k in required if not prompt.get(k)]

    issues = []
    if missing:
        issues.append({"type": "missing_prompt_field", "fields": missing})

    if "quality_gate" not in prompt.get("sections", {}):
        issues.append({"type": "missing_quality_gate"})

    return {
        "qa_id": "O10-PROMPT-QA",
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "checks": {
            "has_prompt_text": bool(prompt.get("prompt_text")),
            "has_techniques": bool(prompt.get("techniques_used")),
            "has_format": bool(prompt.get("output_format")),
            "has_quality_gate": "quality_gate" in prompt.get("sections", {}),
        },
    }
