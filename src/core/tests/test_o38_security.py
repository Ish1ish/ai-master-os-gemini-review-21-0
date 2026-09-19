import http.client
import os
import tempfile
import threading
import unittest

from src.auth import build_default_production_authenticator
from src.identity import IdentityProvider, Principal
from src.http_server import O32HTTPServer
from src.api_adapter import O32APIAdapter
from src.service import ApplicationService


class _NoOpRuntime:
    def run(self, *args, **kwargs):
        return {"status": "COMPLETE"}


class TestO38Security(unittest.TestCase):
    def setUp(self):
        self.old_env = dict(os.environ)
        os.environ["AI_OS_ENV"] = "production"
        os.environ["AI_OS_IDENTITY_SIGNING_SECRET"] = "unit-test-production-signing-secret"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)

    def test_production_identity_secret_required(self):
        os.environ.pop("AI_OS_IDENTITY_SIGNING_SECRET", None)
        with self.assertRaises(RuntimeError):
            IdentityProvider()

    def test_authenticated_http_boundary_rejects_missing_bearer(self):
        with tempfile.TemporaryDirectory() as td:
            auth, _identity = build_default_production_authenticator()
            service = ApplicationService(db_path=td + "/jobs.sqlite3", authenticator=auth, runtime=_NoOpRuntime())
            api = O32APIAdapter(service)
            server = O32HTTPServer(api, "127.0.0.1", 0, require_auth=True)
            thread = threading.Thread(target=server.start, daemon=True)
            thread.start()
            port = server.server.server_port
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
                conn.request("POST", "/runs", body='{"project_id":"P1","request":"test"}', headers={"Content-Type":"application/json"})
                response = conn.getresponse()
                self.assertEqual(response.status, 401)
                response.read()
                conn.close()
            finally:
                server.shutdown()
                thread.join(timeout=3)
                service.close()

    def test_signed_bearer_allows_submit_scope(self):
        with tempfile.TemporaryDirectory() as td:
            auth, identity = build_default_production_authenticator()
            identity.register(Principal("submitter-01", "service", frozenset(), frozenset({"run:submit", "run:read", "run:cancel"})))
            token = identity.issue_token("submitter-01")["token"]
            service = ApplicationService(db_path=td + "/jobs.sqlite3", authenticator=auth, runtime=_NoOpRuntime())
            out = service.submit("P1", "test", credentials={"bearer_token": token})
            self.assertEqual(out["status"], "QUEUED")
            service.close()

    def test_production_startup_fails_without_required_environment(self):
        from src.startup import run_startup_checks
        for name in ["AI_OS_ENV", "AI_OS_IDENTITY_SIGNING_SECRET", "AI_OS_MODEL_BASE_URL", "AI_OS_MODEL_API_KEY", "AI_OS_MODEL_NAME", "AI_OS_SEARCH_BASE_URL", "AI_OS_SEARCH_API_KEY", "AI_OS_MEMORY_DB_PATH", "AI_OS_AUDIT_DB_PATH"]:
            os.environ.pop(name, None)
        os.environ["AI_OS_ENV"] = "production"
        result = run_startup_checks(os.getcwd())
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("AI_OS_IDENTITY_SIGNING_SECRET", result["checks"][-1]["missing"])

    def test_production_service_requires_live_provider_configuration(self):
        with tempfile.TemporaryDirectory() as td:
            for name in ["AI_OS_MODEL_BASE_URL", "AI_OS_MODEL_API_KEY", "AI_OS_MODEL_NAME", "AI_OS_SEARCH_BASE_URL", "AI_OS_SEARCH_API_KEY"]:
                os.environ.pop(name, None)
            with self.assertRaises(RuntimeError):
                ApplicationService(db_path=td + "/jobs.sqlite3", authenticator=build_default_production_authenticator()[0])

    def test_authenticated_http_submit_succeeds_with_signed_bearer(self):
        with tempfile.TemporaryDirectory() as td:
            auth, identity = build_default_production_authenticator()
            identity.register(Principal("submitter-01", "service", frozenset(), frozenset({"run:submit", "run:read", "run:cancel"})))
            token = identity.issue_token("submitter-01")["token"]
            service = ApplicationService(db_path=td + "/jobs.sqlite3", authenticator=auth, runtime=_NoOpRuntime())
            api = O32APIAdapter(service)
            server = O32HTTPServer(api, "127.0.0.1", 0, require_auth=True)
            thread = threading.Thread(target=server.start, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection("127.0.0.1", server.server.server_port, timeout=3)
                body = '{"project_id":"P1","request":"test"}'
                conn.request("POST", "/runs", body=body, headers={"Content-Type":"application/json", "Authorization": f"Bearer {token}"})
                response = conn.getresponse()
                self.assertEqual(response.status, 202)
                data = response.read().decode("utf-8")
                self.assertIn("QUEUED", data)
                conn.close()
            finally:
                server.shutdown()
                thread.join(timeout=3)
                service.close()

    def test_tampered_bearer_rejected(self):
        auth, identity = build_default_production_authenticator()
        identity.register(Principal("submitter-01", "service", frozenset(), frozenset({"run:submit"})))
        token = identity.issue_token("submitter-01")["token"]
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        self.assertEqual(auth.authenticate({"bearer_token": tampered})["status"], "UNAUTHENTICATED")

    def test_legacy_principal_id_is_rejected(self):
        auth, _identity = build_default_production_authenticator()
        self.assertEqual(auth.authenticate({"principal_id": "viewer-01"})["status"], "UNAUTHENTICATED")


if __name__ == "__main__":
    unittest.main()
