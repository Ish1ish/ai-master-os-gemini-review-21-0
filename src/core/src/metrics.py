import time


class OperatorMetrics:
    def __init__(self, queue_service):
        self.qs=queue_service

    def snapshot(self):
        queue=self.qs.queue
        return {
            "queue_depth":len(queue.list_status("QUEUED")),
            "running":len(queue.list_status("RUNNING")),
            "failed":len(queue.list_status("FAILED")),
            "dead_letters":len(self.qs.dead_letter.list_all()),
            "timestamp":time.time(),
        }
