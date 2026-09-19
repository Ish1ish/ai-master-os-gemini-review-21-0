from .classifier import classify_memory_event
from .learning import build_learning_record
from .store import MemoryStore
from .sqlite_store import SQLiteMemoryStore

class MemoryLearningRuntime:
    def __init__(self, store=None, storage_path=None):
        self.store = store or (SQLiteMemoryStore(storage_path) if storage_path else MemoryStore())

    def process_run(self, run_result, qa_result=None):
        if qa_result and qa_result.get("status")!="PASS":
            return {"status":"SKIPPED","reason":"qa_not_passed","memory_refs":[],"learning_ref":None}

        refs=[]
        for obj in classify_memory_event(run_result)["events"]:
            refs.append(self.store.write(obj)["object_id"])

        lesson=build_learning_record(run_result,qa_result)
        learning_ref=None
        if lesson:
            self.store.write({
                "object_type":"Lesson","object_id":lesson["lesson_id"],"version":lesson["version"],
                "project_id":lesson["project_id"],"summary":lesson["summary"],"scope":lesson["scope"],
                "confidence":lesson["confidence"],"source_refs":lesson["source_refs"],"status":lesson["status"]
            })
            learning_ref=lesson["lesson_id"]

        return {"status":"WRITTEN","memory_refs":refs,"learning_ref":learning_ref,"learning":lesson}

    def close(self):
        close = getattr(self.store, "close", None)
        if callable(close):
            close()
