
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class O34Handler(BaseHTTPRequestHandler):
    service=None
    require_auth=False

    def _send(self, status, payload):
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _credentials(self):
        auth = self.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            return {"bearer_token": auth[7:].strip()}
        return {}

    def _auth_gate(self, action, scope):
        if not self.require_auth:
            return self._credentials()
        credentials = self._credentials()
        result = self.service.app._authorize(credentials, action, scope)
        if result.get("status") != "ALLOW":
            status = 401 if result.get("status") == "UNAUTHORIZED" else 403
            self._send(status, result)
            return False
        return credentials

    def _body(self):
        n=int(self.headers.get("Content-Length","0"))
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

    def do_GET(self):
        path=urlparse(self.path).path
        if path.startswith("/counterfactual/memory/"):
            project_id = path.split("/")[-1]
            gate = self._auth_gate("read_counterfactual_memory", "counterfactual:read")
            if gate is False:
                return
            return self._send(200, self.service.app.get_counterfactual_memory(project_id, credentials=gate))
        if path=="/health":
            return self._send(200,{"status":"OK"})
        if path=="/readiness":
            return self._send(200,self.service.readiness())
        if path=="/control/dashboard":
            gate = self._auth_gate("control_dashboard", "control:read")
            if gate is False:
                return
            return self._send(200,self.service.dashboard())
        if path.startswith("/control/actions/"):
            target=path.split("/")[-1]
            gate = self._auth_gate("control_actions", "control:read")
            if gate is False:
                return
            return self._send(200,{"actions":self.service.operator_actions(target)})
        if path.startswith("/control/actions"):
            gate = self._auth_gate("control_actions", "control:read")
            if gate is False:
                return
            return self._send(200,{"actions":self.service.operator_actions()})
        if path.startswith("/runs/"):
            job_id=path.split("/")[-1]
            gate = self._auth_gate("read_run", "run:read")
            if gate is False:
                return
            out=self.service.status(job_id)
            return self._send(200 if out else 404, out or {"status":"NOT_FOUND"})
        return self._send(404,{"status":"NOT_FOUND"})

    def do_POST(self):
        path=urlparse(self.path).path
        try:
            body=self._body()
        except Exception as exc:
            return self._send(400,{"status":"BAD_REQUEST","error":str(exc)})

        if path=="/counterfactual/memory/predictions":
            gate = self._auth_gate("record_counterfactual_prediction", "counterfactual:record")
            if gate is False:
                return
            return self._send(200, self.service.app.record_counterfactual_prediction(body, credentials=gate))
        if path=="/counterfactual/memory/outcomes":
            gate = self._auth_gate("observe_counterfactual_outcome", "counterfactual:observe")
            if gate is False:
                return
            try:
                return self._send(200, self.service.app.observe_counterfactual_outcome(body, credentials=gate))
            except (KeyError, ValueError) as exc:
                return self._send(400, {"status":"BLOCK", "reason":str(exc)})
        if path=="/runs":
            gate = self._auth_gate("submit_run", "run:submit")
            if gate is False:
                return
            out=self.service.submit(body, credentials=gate)
            return self._send(202 if out.get("status")=="QUEUED" else 400,out)

        if path.startswith("/runs/") and path.endswith("/cancel"):
            job_id=path.split("/")[-2]
            gate = self._auth_gate("cancel_run", "run:cancel")
            if gate is False:
                return
            operator_id = ((gate.get("auth") or {}).get("principal") if isinstance(gate, dict) else None) or body.get("operator_id","operator")
            return self._send(200,self.service.cancel(job_id, operator_id))

        if path.startswith("/runs/") and path.endswith("/retry"):
            job_id=path.split("/")[-2]
            gate = self._auth_gate("retry_run", "run:retry")
            if gate is False:
                return
            return self._send(200,self.service.retry_failed(job_id,body.get("operator_id","operator")))

        if path.startswith("/runs/") and path.endswith("/recover"):
            gate = self._auth_gate("recover_queue", "queue:recover")
            if gate is False:
                return
            return self._send(200,self.service.recover(body.get("operator_id","operator")))

        if path.startswith("/dead-letters/") and path.endswith("/replay"):
            job_id=path.split("/")[-2]
            gate = self._auth_gate("replay_dead_letter", "dlq:replay")
            if gate is False:
                return
            return self._send(200,self.service.replay_dead_letter(job_id,body.get("operator_id","operator")))

        if path=="/workers/run-once":
            gate = self._auth_gate("worker_run_once", "job:execute")
            if gate is False:
                return
            return self._send(200,self.service.worker_once(body.get("worker_id","o34-worker")))

        return self._send(404,{"status":"NOT_FOUND"})

    def log_message(self,*args):
        return


class UnifiedAPIServer:
    def __init__(self, service, host="127.0.0.1", port=0, require_auth=None):
        if require_auth is None:
            require_auth = os.getenv("AI_OS_ENV", "local").strip().lower() in {"prod", "production"}
        O34Handler.service=service
        O34Handler.require_auth=bool(require_auth)
        self.server=ThreadingHTTPServer((host,port),O34Handler)

    def start(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
        self.server.server_close()
