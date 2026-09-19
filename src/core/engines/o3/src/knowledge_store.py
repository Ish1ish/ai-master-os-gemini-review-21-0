import json
from pathlib import Path
from typing import Dict, List
from .models import KnowledgeItem


class KnowledgeStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.items: Dict[str, KnowledgeItem] = {}

    def load(self) -> None:
        self.items.clear()
        for path in sorted(self.root.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            for raw in data.get("items", []):
                item = KnowledgeItem(**raw)
                if item.status != "active":
                    continue
                self.items[item.knowledge_id] = item

    def get(self, knowledge_id: str) -> KnowledgeItem | None:
        return self.items.get(knowledge_id)

    def all(self) -> List[KnowledgeItem]:
        return list(self.items.values())

    def search(self, terms: List[str], scope: str = "global", limit: int = 8) -> List[KnowledgeItem]:
        norm_terms = [t.lower() for t in terms if t.strip()]
        scored = []
        for item in self.items.values():
            if item.scope not in {scope, "global"}:
                continue
            haystack = f"{item.title} {item.content} {' '.join(item.tags)}".lower()
            score = sum(1 for t in norm_terms if t in haystack)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda x: (-x[0], x[1].knowledge_id))
        return [item for _, item in scored[:limit]]
