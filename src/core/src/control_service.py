
import os

from .auth import build_default_production_authenticator
from .service import ApplicationService
from .queue_service import QueueService
from .operator_store import OperatorStore
from .control_plane import OperatorControlPlane
from .api_adapter import O32APIAdapter


class FullControlService:
    def __init__(self, root, authenticator=None):
        os.makedirs(root, exist_ok=True)
        self.root=root
        jobs=os.path.join(root,"jobs.sqlite3")
        queue=os.path.join(root,"queue.sqlite3")
        dlq=os.path.join(root,"dead_letter.sqlite3")
        operator=os.path.join(root,"operator.sqlite3")

        production = os.getenv("AI_OS_ENV", "local").strip().lower() in {"prod", "production"}
        if production and authenticator is None:
            authenticator, _identity = build_default_production_authenticator()
        self.app=ApplicationService(db_path=jobs, authenticator=authenticator)
        self.queue_service=QueueService(
            job_db=jobs,
            queue_db=queue,
            dead_letter_db=dlq,
            application_service=self.app,
        )
        self.operator_store=OperatorStore(operator)
        self.control=OperatorControlPlane(self.queue_service,self.operator_store)
        self.api=O32APIAdapter(self.app)
        self._closed=False

    def submit(self, body, credentials=None):
        out=self.api.post_run(body, credentials=credentials)
        if out.get("status")=="QUEUED":
            self.queue_service.queue.enqueue(
                out["job_id"],
                {
                    "job_id":out["job_id"],
                    "project_id":body["project_id"],
                    "request":body["request"],
                    "audience":body.get("audience","small businesses using AI tools"),
                    "goal":body.get("goal","validate a lean business opportunity"),
                    "constraints":body.get("constraints"),
                },
                available_at=0,
            )
        return out

    def worker_once(self, worker_id="o34-worker"):
        return self.queue_service.worker(worker_id=worker_id,max_attempts=3).run_once()

    def status(self, job_id):
        app_job=self.app.jobs.get(job_id)
        queue_job=self.queue_service.queue.get(job_id)
        if app_job and app_job.get("status") in {"COMPLETE","FAILED","CANCELLED"}:
            return app_job
        if queue_job:
            return queue_job
        return app_job

    def inspect(self, job_id):
        return self.control.inspect(job_id)

    def cancel(self, job_id, operator_id="operator"):
        return self.control.cancel(job_id, operator_id)

    def retry_failed(self, job_id, operator_id="operator"):
        return self.control.retry_failed(job_id, operator_id)

    def recover(self, operator_id="operator", now=None):
        return self.control.recover_expired(operator_id, now)

    def replay_dead_letter(self, job_id, operator_id="operator"):
        return self.control.replay_dead_letter(job_id, operator_id)

    def dashboard(self):
        return self.control.overview()

    def operator_actions(self, target_id=None):
        return self.operator_store.list_actions(target_id)

    def close(self):
        """Close control-plane resources in dependency order. Idempotent."""
        if getattr(self, "_closed", False):
            return
        self._closed=True
        errors=[]
        for obj in (self.operator_store, self.queue_service, self.app):
            try:
                obj.close()
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise errors[0]

    def __enter__(self):
        if getattr(self, "_closed", False):
            raise RuntimeError("FullControlService is closed")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def readiness(self):
        return {
            "status":"HEALTHY",
            "components":{
                "application_service":"UP",
                "durable_queue":"UP",
                "operator_control":"UP",
                "approval_boundary":"UP",
                "persistent_audit":"UP",
            },
        }
