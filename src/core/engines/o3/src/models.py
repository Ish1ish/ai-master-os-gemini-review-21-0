from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class KnowledgeItem:
    knowledge_id: str
    title: str
    content: str
    source_refs: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    confidence: str = "medium"
    freshness: str = "static"
    scope: str = "global"
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "title": self.title,
            "content": self.content,
            "source_refs": self.source_refs,
            "tags": self.tags,
            "confidence": self.confidence,
            "freshness": self.freshness,
            "scope": self.scope,
            "status": self.status,
        }
