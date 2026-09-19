import os
from pathlib import Path

from .service_commands import api_command, worker_smoke_command
from .startup import run_startup_checks
from .supervisor import ProcessSupervisor
from .deployment_health import DeploymentHealth
from .shutdown import GracefulShutdown
from .qa import validate_deployment_output


class O31Runtime:
    def __init__(self, root=None, commands=None):
        self.root=str(root or Path(__file__).resolve().parents[1])
        self.commands=commands or {
            "api_smoke": api_command(),
            "worker_smoke": worker_smoke_command(),
        }
        self.supervisor=ProcessSupervisor(self.commands)
        self.health=DeploymentHealth()
        self.shutdown=GracefulShutdown()

    def startup(self):
        return run_startup_checks(self.root)

    def deploy_smoke(self):
        startup=self.startup()
        if startup["status"]!="PASS":
            return {"status":"FAILED","startup_check":startup}

        started=self.supervisor.start()
        health=self.supervisor.health()
        smoke=self.health.smoke(self.supervisor)
        shutdown=self.shutdown.stop(self.supervisor)

        out={
            "status":"DRAFT",
            "engine_id":"E-23",
            "engine_version":"O31-v1.0",
            "startup_check":startup,
            "start":started,
            "health":health,
            "smoke":smoke,
            "shutdown":shutdown,
        }
        qa=validate_deployment_output(out)
        out["qa"]=qa
        out["status"]="COMPLETE" if qa["status"]=="PASS" else "FAILED"
        return out
