import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class O36Handler(BaseHTTPRequestHandler):
    service = None
    authz = None
    governed = None

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(n).decode()) if n else {}

    def _credentials(self):
        auth = self.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            return {"bearer_token": auth[7:].strip()}
        return {}

    def do_GET(self):
        path = urlparse(self.path).path
        creds = self._credentials()

        if path == "/identity/me":
            auth = self.authz.authenticate(creds)
            return self._send(200 if auth["status"] == "AUTHENTICATED" else 401, auth)

        if path == "/approvals/pending":
            auth = self.authz.authorize(creds, "approval", "read")
            if auth["status"] != "ALLOW":
                return self._send(403, auth)
            return self._send(200, {"approvals": self.service.pending()})

        if path.startswith("/approvals/"):
            auth = self.authz.authorize(creds, "approval", "read")
            if auth["status"] != "ALLOW":
                return self._send(403, auth)
            a = self.service.get_approval(path.split("/")[-1])
            return self._send(200 if a else 404, a or {"status": "NOT_FOUND"})

        return self._send(404, {"status": "NOT_FOUND"})

    def do_POST(self):
        path = urlparse(self.path).path
        creds = self._credentials()
        try:
            body = self._body()
        except Exception as exc:
            return self._send(400, {"status": "BAD_REQUEST", "error": str(exc)})

        if path.startswith("/approvals/") and path.endswith("/decision"):
            auth = self.authz.authorize(creds, "approval", "decide")
            if auth["status"] != "ALLOW":
                return self._send(403, auth)
            result = self.governed.decide(creds, path.split("/")[-2], body.get("decision"), body.get("reason", ""))
            return self._send(200 if result.get("status") in {"APPROVED", "REJECTED", "CONFLICT"} else 403, result)

        return self._send(404, {"status": "NOT_FOUND"})

    def log_message(self, *args):
        return


class O36AuthorizationServer:
    def __init__(self, service, authz, host="127.0.0.1", port=0):
        from .governed_control import GovernedControl
        self.service = service
        self.authz = authz
        self.governed = GovernedControl(service, authz)
        O36Handler.service = service
        O36Handler.authz = authz
        O36Handler.governed = self.governed
        self.server = ThreadingHTTPServer((host, port), O36Handler)

    def start(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
        self.server.server_close()
