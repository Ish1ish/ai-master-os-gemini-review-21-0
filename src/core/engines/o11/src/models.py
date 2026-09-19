from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class SourceRecord:
    source_id: str
    title: str
    url: str
    source_type: str = "web"
    published_at: str = ""
    accessed_at: str = ""
    authority: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceItem:
    evidence_id: str
    claim: str
    source_id: str
    excerpt: str = ""
    confidence: str = "medium"
    freshness: str = "current"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
