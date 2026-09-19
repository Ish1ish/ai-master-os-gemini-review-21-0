from typing import Any, Dict, List


def bind_provenance(knowledge_pack: Dict[str, Any]) -> Dict[str, Any]:
    refs: List[Dict[str, Any]] = []
    for item in knowledge_pack.get("items", []):
        refs.append({
            "knowledge_id": item["knowledge_id"],
            "title": item["title"],
            "source_refs": item.get("source_refs", []),
            "freshness": item.get("freshness", "unknown"),
            "confidence": item.get("confidence", "unknown"),
        })
    return {
        "source_refs": knowledge_pack.get("source_refs", []),
        "bindings": refs,
    }
