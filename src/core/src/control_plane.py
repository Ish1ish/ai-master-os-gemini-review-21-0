from .health import O27Health


class OperatorControlPlane:
    """
    Central operational interface over queue, jobs, DLQ and worker state.
    """

    def __init__(self, queue_service, operator_store=None):
        self.qs=queue_service
        self.store=operator_store

    def overview(self):
        return {
            "queue": {
                "queued": len(self.qs.queue.list_status("QUEUED")),
                "running": len(self.qs.queue.list_status("RUNNING")),
                "complete": len(self.qs.queue.list_status("COMPLETE")),
                "failed": len(self.qs.queue.list_status("FAILED")),
                "cancelled": len(self.qs.queue.list_status("CANCELLED")),
            },
            "dead_letters": len(self.qs.dead_letter.list_all()),
        }

    def inspect(self, job_id):
        return {
            "job": self.qs.queue.get(job_id),
            "dead_letter": self.qs.dead_letter.get(job_id),
            "operator_actions": self.store.list_actions(job_id) if self.store else [],
        }

    def cancel(self, job_id, operator_id="operator"):
        ok=self.qs.queue.cancel(job_id)
        status="CANCELLED" if ok else "NO_CHANGE"
        if self.store:
            self.store.record(operator_id,"cancel",job_id,status=status)
        return {"status":status,"job_id":job_id}

    def recover_expired(self, operator_id="operator", now=None):
        count=self.qs.recover(now=now)
        if self.store:
            self.store.record(operator_id,"recover_expired","QUEUE",{"count":count})
        return {"status":"RECOVERED","count":count}

    def retry_failed(self, job_id, operator_id="operator"):
        job=self.qs.queue.get(job_id)
        if not job:
            return {"status":"NOT_FOUND","job_id":job_id}
        if job["status"]!="FAILED":
            return {"status":"NO_CHANGE","reason":"job_not_failed","current_status":job["status"]}
        # Manual retry resets queue state without modifying attempt history semantics outside this request.
        self.qs.queue.conn.execute(
            "UPDATE queue_jobs SET status='QUEUED', available_at=0, lease_until=NULL, worker_id=NULL, last_error=NULL, updated_at=CURRENT_TIMESTAMP WHERE job_id=?",
            (job_id,)
        )
        self.qs.queue.conn.commit()
        if self.store:
            self.store.record(operator_id,"retry_failed",job_id,status="QUEUED")
        return {"status":"QUEUED","job_id":job_id}

    def replay_dead_letter(self, job_id, operator_id="operator"):
        dl=self.qs.dead_letter.get(job_id)
        if not dl:
            return {"status":"NOT_FOUND","job_id":job_id}
        existing=self.qs.queue.get(job_id)
        if existing:
            return {"status":"CONFLICT","reason":"job_exists_in_queue","job_id":job_id}
        self.qs.queue.enqueue(job_id,dl["payload"],available_at=0)
        if self.store:
            self.store.record(operator_id,"replay_dead_letter",job_id,status="QUEUED")
        return {"status":"QUEUED","job_id":job_id}

    def health(self):
        return O27Health().check(self.qs.queue,self.qs.dead_letter)
