import argparse
import os
import signal
import time

from .queue_service import QueueService


class WorkerProcess:
    def __init__(self, queue_service=None, worker_id=None, max_attempts=3, poll_seconds=0.2):
        self.queue_service=queue_service or QueueService()
        self.worker=self.queue_service.worker(worker_id=worker_id,max_attempts=max_attempts)
        self.poll_seconds=poll_seconds
        self.running=True

    def stop(self, signum=None, frame=None):
        self.running=False

    def run_forever(self):
        while self.running:
            result=self.worker.run_once()
            if result.get("status")=="IDLE":
                time.sleep(self.poll_seconds)
        return {"status":"STOPPED","worker_id":self.worker.worker_id}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--worker-id",default=None)
    args=parser.parse_args()

    wp=WorkerProcess(worker_id=args.worker_id)
    signal.signal(signal.SIGINT,wp.stop)
    signal.signal(signal.SIGTERM,wp.stop)
    print(wp.run_forever())


if __name__=="__main__":
    main()
