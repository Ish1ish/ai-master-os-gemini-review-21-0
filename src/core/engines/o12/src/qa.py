from typing import Dict, Any


def validate_idea_output(themes_pack: Dict[str, Any],
                         ideas_pack: Dict[str, Any],
                         scores_pack: Dict[str, Any],
                         validation_pack: Dict[str, Any]) -> Dict[str, Any]:
    issues = []

    if themes_pack.get("themes") and not ideas_pack.get("ideas"):
        issues.append({"type": "themes_without_ideas"})

    for idea in ideas_pack.get("ideas", []):
        if not idea.get("source_refs") and idea.get("origin_theme"):
            issues.append({
                "type": "unbound_idea",
                "idea_id": idea.get("idea_id"),
            })

    if scores_pack.get("ranked_ideas") and not validation_pack.get("idea_validation_plans"):
        issues.append({"type": "missing_validation_plans"})

    return {
        "qa_id": "O12-IDEA-QA",
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "checks": {
            "themes": bool(themes_pack.get("themes")),
            "ideas": bool(ideas_pack.get("ideas")),
            "scored": bool(scores_pack.get("ranked_ideas")),
            "validation": bool(validation_pack.get("idea_validation_plans")),
        },
    }
