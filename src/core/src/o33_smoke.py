import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import json
import os
import tempfile
import threading
from urllib.request import Request, urlopen

from .service import ApplicationService
from .api_adapter import O32APIAdapter
from .http_server import O32HTTPServer
from .queue_service import QueueService
from .worker_daemon import WorkerDaemon
from .qa import validate_deployment


def run_smoke():
    td=tempfile.TemporaryDirectory()
    jobs=os.path.join(td.name,"jobs.sqlite3")
    queue=os.path.join(td.name,"queue.sqlite3")
    dlq=os.path.join(td.name,"dlq.sqlite3")

    # Shared QueueService points at the same persistent databases used by the service.
    app=ApplicationService(db_path=jobs)
    qs=QueueService(
        job_db=jobs,
        queue_db=queue,
        dead_letter_db=dlq,
        application_service=app,
    )
    api=O32APIAdapter(app)
    server=O32HTTPServer(api,host="127.0.0.1",port=0)
    server_thread=threading.Thread(target=server.start,daemon=True)
    server_thread.start()

    port=server.server.server_port
    with urlopen(f"http://127.0.0.1:{port}/health",timeout=2) as r:
        api_health=json.loads(r.read().decode())

    created=api.post_run({
        "project_id":"O33-SMOKE",
        "request":"Find a lean AI business opportunity",
    })

    # Bridge the service-created job into the durable queue, then let the worker daemon consume it.
    qs.queue.enqueue(created["job_id"],{
        "job_id":created["job_id"],
        "project_id":"O33-SMOKE",
        "request":"Find a lean AI business opportunity",
        "audience":"small businesses using AI tools",
        "goal":"validate a lean business opportunity",
        "constraints":["low startup cost","simple MVP"],
    })

    daemon=WorkerDaemon(qs,worker_id="o33-smoke",poll_seconds=0.01,max_attempts=3)
    result=daemon.run_once()

    worker_shutdown=daemon.run_forever(max_cycles=1)
    stored=qs.queue.get(created["job_id"])

    same_db="SAME_DB" if app.jobs.path==jobs else "MISMATCH"

    server.shutdown()
    server_thread.join(timeout=1)
    daemon.close()
    qs.close()
    app.close()

    out={
        "api_health":api_health,
        "job_created":created,
        "worker_result":result,
        "queue_status":stored["status"] if stored else None,
        "worker_shutdown":worker_shutdown,
        "shared_store":{"status":same_db,"jobs_db":jobs,"queue_db":queue},
    }
    out["qa"]=validate_deployment(out)
    out["status"]="COMPLETE" if out["qa"]["status"]=="PASS" else "FAILED"
    td.cleanup()
    return out
