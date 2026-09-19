import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class O32RequestHandler(BaseHTTPRequestHandler):
    api = None
    require_auth = False

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _credentials(self):
        auth = self.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            return {"bearer_token": auth[7:].strip()}
        return {}

    def _auth_gate(self):
        if not self.require_auth:
            return None
        creds = self._credentials()
        result = self.api.service._authorize(creds, "request", "run:read")
        if result.get("status") != "ALLOW":
            status = 401 if result.get("status") == "UNAUTHORIZED" else 403
            self._send(status, result)
            return False
        return creds

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._send(200, self.api.health())
        if path in {"/readiness", "/ready"}:
            return self._send(200, self.api.readiness())
        gate = self._auth_gate()
        if gate is False:
            return None
        if path == "/runs":
            from urllib.parse import parse_qs
            query = parse_qs(urlparse(self.path).query)
            limit = int((query.get("limit") or [50])[0])
            out = self.api.list_runs(limit=limit, credentials=gate if isinstance(gate, dict) else None)
            return self._send(200, out)
        if path == "/counterfactual/adaptive":
            from urllib.parse import parse_qs
            query = parse_qs(urlparse(self.path).query)
            project_id = (query.get("project_id") or [""])[0]
            candidate_decision = (query.get("candidate_decision") or ["BLOCK"])[0]
            candidate_risk = (query.get("candidate_risk") or ["HIGH"])[0]
            out = self.api.get_adaptive_decision({"project_id": project_id, "candidate_decision": candidate_decision, "candidate_risk": candidate_risk}, credentials=gate if isinstance(gate, dict) else None)
            return self._send(200 if out.get("status") in {"READY", "COLD_START"} else 403 if out.get("status")=="FORBIDDEN" else 400, out)
        if path.startswith("/counterfactual/memory/"):
            project_id = path.split("/")[-1]
            out = self.api.get_counterfactual_memory(project_id, credentials=gate if isinstance(gate, dict) else None)
            return self._send(200 if out.get("status") in {"READY", "EMPTY"} else 403, out)
        if path == "/learning/context":
            from urllib.parse import parse_qs
            query = parse_qs(urlparse(self.path).query)
            project_id = (query.get("project_id") or [""])[0]
            experiment_id = (query.get("experiment_id") or [None])[0]
            out = self.api.get_learning_context(project_id=project_id, current_experiment_id=experiment_id, credentials=gate if isinstance(gate, dict) else None)
            return self._send(200 if out.get("status") in {"READY", "EMPTY"} else 403, out)
        if path == "/governance/decisions":
            from urllib.parse import parse_qs
            query = parse_qs(urlparse(self.path).query)
            project_id = (query.get("project_id") or [None])[0]
            run_id = (query.get("run_id") or [None])[0]
            limit = int((query.get("limit") or [50])[0])
            out = self.api.list_governance_decisions(project_id=project_id, run_id=run_id, limit=limit, credentials=gate if isinstance(gate, dict) else None)
            return self._send(200, out)
        if path == "/approvals/pending":
            from urllib.parse import parse_qs
            query = parse_qs(urlparse(self.path).query)
            project_id = (query.get("project_id") or [None])[0]
            out = self.api.list_pending_approvals(project_id=project_id, credentials=gate if isinstance(gate, dict) else None)
            return self._send(200, out)
        if path.startswith("/governance/decisions/"):
            out = self.api.get_governance_decision(path.split("/")[-1], credentials=gate if isinstance(gate, dict) else None)
            return self._send(200 if out.get("status") != "NOT_FOUND" else 404, out)
        if path.startswith("/approvals/"):
            out = self.api.get_approval(path.split("/")[-1], credentials=gate if isinstance(gate, dict) else None)
            return self._send(200 if out.get("status") != "NOT_FOUND" else 404, out)
        if path == "/experiments":
            query = {}
            if "?" in self.path:
                from urllib.parse import parse_qs
                query = parse_qs(urlparse(self.path).query)
            project_id = (query.get("project_id") or [None])[0]
            limit = int((query.get("limit") or [50])[0])
            out = self.api.list_experiments(project_id=project_id, limit=limit, credentials=gate if isinstance(gate, dict) else None)
            return self._send(200, out)
        if path.startswith("/experiments/"):
            out = self.api.get_experiment(path.split("/")[-1], gate if isinstance(gate, dict) else None)
            return self._send(200 if out and out.get("status") != "NOT_FOUND" else 404, out or {"status":"NOT_FOUND"})
        if path.startswith("/runs/"):
            out = self.api.get_run(path.split("/")[-1], gate if isinstance(gate, dict) else None)
            return self._send(200 if out.get("status") != "NOT_FOUND" else 404, out)
        return self._send(404, {"status": "NOT_FOUND"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self._read_json()
        except Exception as exc:
            return self._send(400, {"status": "BAD_REQUEST", "error": str(exc)})

        gate = self._auth_gate()
        if gate is False:
            return None
        creds = gate if isinstance(gate, dict) else None

        if path == "/counterfactual/adaptive":
            try:
                out = self.api.get_adaptive_decision(body, creds)
                code = 200 if out.get("status") in {"READY", "COLD_START"} else 401 if out.get("status")=="UNAUTHORIZED" else 403 if out.get("status")=="FORBIDDEN" else 400
            except (KeyError, ValueError) as exc:
                out = {"status":"BLOCK","reason":str(exc)}; code = 400
            return self._send(code, out)

        if path == "/counterfactual/delta":
            out = self.api.compare_counterfactual(body, creds)
            code = 200 if out.get("status") == "PASS" else 401 if out.get("status") == "UNAUTHORIZED" else 403 if out.get("status") == "FORBIDDEN" else 400
            return self._send(code, out)

        if path == "/counterfactual/preflight":
            out = self.api.simulate_counterfactual(body, creds)
            code = 200 if out.get("status") in {"PASS", "REVIEW", "BLOCK"} else 401 if out.get("status") == "UNAUTHORIZED" else 403 if out.get("status") == "FORBIDDEN" else 400
            return self._send(code, out)

        if path == "/counterfactual/memory/predictions":
            try:
                out = self.api.record_counterfactual_prediction(body, creds)
                code = 200 if out.get("prediction_id") else 401 if out.get("status") == "UNAUTHORIZED" else 403 if out.get("status") == "FORBIDDEN" else 400
            except ValueError as exc:
                out = {"status":"BLOCK","reason":str(exc)}; code = 400
            return self._send(code, out)

        if path == "/counterfactual/memory/outcomes":
            try:
                out = self.api.observe_counterfactual_outcome(body, creds)
                code = 200 if out.get("status") == "OBSERVED" else 401 if out.get("status") == "UNAUTHORIZED" else 403 if out.get("status") == "FORBIDDEN" else 400
            except (KeyError, ValueError) as exc:
                out = {"status":"BLOCK","reason":str(exc)}; code = 400
            return self._send(code, out)

        if path == "/governance/evaluate":
            out = self.api.evaluate_governance(body, creds)
            code = 200 if out.get("decision") in {"AUTO_ALLOW","REVIEW","BLOCK"} else 401 if out.get("status")=="UNAUTHORIZED" else 403 if out.get("status")=="FORBIDDEN" else 400
            return self._send(code, out)

        if path.startswith("/approvals/") and path.endswith("/decision"):
            approval_id = path.split("/")[-2]
            out = self.api.decide_approval(approval_id, body, creds)
            code = 200 if out.get("status") in {"APPROVED","REJECTED","CONFLICT"} else 401 if out.get("status")=="UNAUTHORIZED" else 403 if out.get("status") in {"FORBIDDEN","DENY"} else 404 if out.get("status")=="NOT_FOUND" else 400
            return self._send(code, out)
        if path == "/experiments/from-run":
            out = self.api.create_experiment_from_run(str(body.get("run_id") or ""), creds)
            code = 201 if out.get("experiment_id") else 404 if out.get("status") == "NOT_FOUND" else 409 if out.get("status") == "CONFLICT" else 401 if out.get("status") == "UNAUTHORIZED" else 403 if out.get("status") == "FORBIDDEN" else 400
            return self._send(code, out)

        if path.startswith("/experiments/") and path.endswith("/evidence"):
            experiment_id = path.split("/")[-2]
            out = self.api.record_experiment_evidence(experiment_id, body, creds)
            code = 200 if out.get("status") in {"EVIDENCE_RECORDED", "CONCLUDED", "INCONCLUSIVE", "READY"} else 404 if out.get("status")=="NOT_FOUND" else 401 if out.get("status")=="UNAUTHORIZED" else 403 if out.get("status")=="FORBIDDEN" else 400
            return self._send(code, out)

        if path.startswith("/experiments/") and path.endswith("/evaluate"):
            experiment_id = path.split("/")[-2]
            out = self.api.evaluate_experiment(experiment_id, creds)
            code = 200 if out.get("status") in {"CONCLUDED", "INCONCLUSIVE", "EVALUATED"} or out.get("evaluation") else 404 if out.get("status")=="NOT_FOUND" else 401 if out.get("status")=="UNAUTHORIZED" else 403 if out.get("status")=="FORBIDDEN" else 400
            return self._send(code, out)

        if path == "/runs":
            out = self.api.post_run(body, creds)
            code = 202 if out.get("status") == "QUEUED" else (401 if out.get("status") == "UNAUTHORIZED" else 403 if out.get("status") == "FORBIDDEN" else 400)
            return self._send(code, out)

        if path.endswith("/cancel") and path.startswith("/runs/"):
            job_id = path.split("/")[-2]
            out = self.api.cancel_run(job_id, creds)
            code = 200 if out.get("status") in {"CANCELLED", "NO_CHANGE", "CONFLICT"} else 401 if out.get("status") == "UNAUTHORIZED" else 403 if out.get("status") == "FORBIDDEN" else 404
            return self._send(code, out)

        if path.endswith("/execute") and path.startswith("/runs/"):
            job_id = path.split("/")[-2]
            authz = self.api.service._authorize(creds, "execute_run", "run:execute") if creds is not None else {"status":"ALLOW"}
            if authz.get("status") != "ALLOW":
                return self._send(401 if authz.get("status") == "UNAUTHORIZED" else 403, authz)
            out = self.api.run_now(job_id, body, creds)
            code = 200 if out.get("status") in {"COMPLETE", "FAILED", "CANCELLED", "RUNNING"} else 404 if out.get("status")=="NOT_FOUND" else 401 if out.get("status")=="UNAUTHORIZED" else 403 if out.get("status")=="FORBIDDEN" else 409
            return self._send(code, out)

        return self._send(404, {"status": "NOT_FOUND"})

    def log_message(self, format, *args):
        return


class O32HTTPServer:
    def __init__(self, api, host="127.0.0.1", port=8080, require_auth=False):
        O32RequestHandler.api = api
        O32RequestHandler.require_auth = bool(require_auth)
        self.server = ThreadingHTTPServer((host, port), O32RequestHandler)

    def start(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
        self.server.server_close()
