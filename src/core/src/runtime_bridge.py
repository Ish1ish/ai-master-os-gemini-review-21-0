import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import os
from .queue_service import QueueService
from .service import ApplicationService
from .providers import fake_model_provider, fake_search_provider
from .real_wiring import O23Runtime


class O22Bridge:
    def __init__(self, root):
        job_db=os.path.join(root,"jobs.sqlite3")
        self.runtime=O23Runtime(
            model_provider=fake_model_provider,
            search_provider=fake_search_provider,
            memory_path=None,
            audit_path=None,
        )
        self.app=ApplicationService(db_path=job_db, runtime=self.runtime)

    def run(self, run_id, project_id, request):
        # Execute directly through the integrated runtime for deterministic evaluation.
        return self.runtime.run(
            run_id,project_id,request,
            audience="small businesses using AI tools",
            goal="validate a lean business opportunity",
            constraints=["low startup cost","simple MVP"],
        )


    def close(self):
        if getattr(self, "_closed", False):
            return
        self._closed = True
        try:
            self.app.close()
        finally:
            close_runtime = getattr(self.runtime, "close", None)
            if callable(close_runtime):
                close_runtime()

    def __enter__(self):
        if getattr(self, "_closed", False):
            raise RuntimeError("O22Bridge is closed")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
