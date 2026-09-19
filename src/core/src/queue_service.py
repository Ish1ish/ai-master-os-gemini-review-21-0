import time
from .queue import DurableQueue
from .dead_letter import DeadLetterStore
from .worker import QueueWorker


class QueueService:
    def __init__(self, job_db="./data/jobs.sqlite3", queue_db="./data/queue.sqlite3", dead_letter_db="./data/dead_letter.sqlite3", application_service=None):
        self._owns_application_service = application_service is None
        if application_service is None:
            from .service import ApplicationService
            application_service = ApplicationService(db_path=job_db)
        self.application_service = application_service
        self.queue = DurableQueue(queue_db)
        self.dead_letter = DeadLetterStore(dead_letter_db)
        self._closed = False

    def _ensure_open(self):
        if self._closed:
            raise RuntimeError("QueueService is closed")

    def submit(self, project_id, request, audience="small businesses using AI tools", goal="validate a lean business opportunity", constraints=None, language="en"):
        self._ensure_open()
        created = self.application_service.submit(project_id=project_id, request=request, audience=audience, goal=goal, constraints=constraints, language=language, internal=True)
        if created.get("status") != "QUEUED":
            return created
        self.queue.enqueue(created["job_id"], {
            "job_id": created["job_id"], "project_id": project_id, "request": request,
            "audience": audience, "goal": goal, "constraints": constraints, "language": language,
        })
        return created

    def worker(self, worker_id=None, max_attempts=3, lease_seconds=60):
        self._ensure_open()
        return QueueWorker(self.queue, self.application_service, self.dead_letter, worker_id, max_attempts, lease_seconds)

    def recover(self, now=None):
        self._ensure_open()
        return self.queue.recover_expired(time.time() if now is None else now)

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.queue.close()
        finally:
            try:
                self.dead_letter.close()
            finally:
                if self._owns_application_service and hasattr(self.application_service, "close"):
                    self.application_service.close()

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
