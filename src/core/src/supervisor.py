import os
import signal
import subprocess
import sys
import time


class ProcessSupervisor:
    """
    Minimal cross-platform supervisor for the local process model.
    It launches API and/or worker commands, records lifecycle state, and
    attempts graceful termination before forceful kill.
    """

    def __init__(self, commands):
        self.commands=commands
        self.processes={}
        self.state="STOPPED"

    def start(self):
        if self.state=="RUNNING":
            return {"status":"NO_CHANGE","state":self.state}

        started=[]
        for name,cmd in self.commands.items():
            proc=subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.processes[name]=proc
            started.append({"name":name,"pid":proc.pid,"command":cmd})

        self.state="RUNNING"
        return {"status":"STARTED","state":self.state,"processes":started}

    def health(self):
        status={}
        for name,proc in self.processes.items():
            status[name]="UP" if proc.poll() is None else f"EXITED:{proc.returncode}"
        healthy=bool(status) and all(v=="UP" for v in status.values())
        return {"status":"HEALTHY" if healthy else "DEGRADED","processes":status}

    def stop(self, grace_seconds=2.0):
        if self.state!="RUNNING":
            return {"status":"NO_CHANGE","state":self.state}

        results=[]
        for name,proc in self.processes.items():
            if proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=grace_seconds)
                    results.append({"name":name,"status":"STOPPED","forced":False})
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=1)
                    results.append({"name":name,"status":"STOPPED","forced":True})
            else:
                results.append({"name":name,"status":"ALREADY_EXITED","forced":False})

        self.state="STOPPED"
        return {"status":"STOPPED","state":self.state,"processes":results}

    def restart(self):
        self.stop()
        return self.start()
