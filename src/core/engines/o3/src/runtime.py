from typing import Any, Dict
from .knowledge_store import KnowledgeStore
from .retriever import retrieve_for_engine, build_knowledge_pack
from .provenance import bind_provenance
from .freshness import check_knowledge_freshness
from .qa import qa_knowledge_aware_run


class O3Runtime:
    def __init__(self, knowledge_root):
        self.store = KnowledgeStore(knowledge_root)
        self.store.load()

    def execute_engine(self, engine_id: str, user_text: str,
                       project_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        items = retrieve_for_engine(self.store, engine_id, user_text, project_context)
        pack = build_knowledge_pack(items)
        provenance = bind_provenance(pack)
        freshness = check_knowledge_freshness(user_text, pack)
        qa = qa_knowledge_aware_run(user_text, pack, provenance, freshness)

        return {
            "engine_id": engine_id,
            "status": "READY_WITH_KNOWLEDGE" if qa["status"] == "PASS" else "READY_WITH_WARNINGS",
            "knowledge_pack": pack,
            "provenance": provenance,
            "freshness": freshness,
            "qa": qa,
            "execution_contract": {
                "task": user_text,
                "project_context": project_context or {},
                "knowledge_ids": pack["knowledge_ids"],
                "source_refs": pack["source_refs"],
            },
        }
