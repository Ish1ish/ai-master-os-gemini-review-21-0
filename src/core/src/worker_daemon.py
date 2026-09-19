import signal
import time

from .queue_service import QueueService


class WorkerDaemon:
    """Long-lived worker daemon with explicit lifecycle ownership."""

    def __init__(self, queue_service=None, worker_id="worker-01", poll_seconds=0.2, max_attempts=3):
        self._owns_queue_service = queue_service is None
        self.queue_service = queue_service or QueueService()
        self.worker_id = worker_id
        self.poll_seconds = poll_seconds
        self.max_attempts = max_attempts
        self.running = True
        self.last_result = None
        self._closed = False

    def stop(self, signum=None, frame=None):
        self.running = False

    def run_once(self):
        if self._closed:
            raise RuntimeError("WorkerDaemon is closed")
        self.last_result = self.queue_service.worker(worker_id=self.worker_id, max_attempts=self.max_attempts).run_once()
        return self.last_result

    def run_forever(self, max_cycles=None):
        if self._closed:
            raise RuntimeError("WorkerDaemon is closed")
        cycles = 0
        while self.running:
            result = self.run_once()
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            if result.get("status") == "IDLE":
                time.sleep(self.poll_seconds)
        self.running = False
        return {"status": "STOPPED", "worker_id": self.worker_id, "cycles": cycles}

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.running = False
        if self._owns_queue_service and hasattr(self.queue_service, "close"):
            self.queue_service.close()

    def __enter__(self):
        if self._closed:
            raise RuntimeError("WorkerDaemon is closed")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def install_signal_handlers(daemon):
    signal.signal(signal.SIGINT, daemon.stop)
    signal.signal(signal.SIGTERM, daemon.stop)
