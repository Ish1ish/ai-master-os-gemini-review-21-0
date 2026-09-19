from dataclasses import dataclass


@dataclass
class SharedDeployment:
    api_host: str
    api_port: int
    jobs_db: str
    queue_db: str
    dead_letter_db: str

    def queue_config(self):
        return {
            "job_db":self.jobs_db,
            "queue_db":self.queue_db,
            "dead_letter_db":self.dead_letter_db,
        }
