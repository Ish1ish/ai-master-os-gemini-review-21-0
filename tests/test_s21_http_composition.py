from __future__ import annotations

import json
import os
import tempfile
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

from unified_runtime.s21_http_launcher import build_s21_http_server


class TestS21HTTPComposition(unittest.TestCase):
    def test_signed_bearer_reaches_canonical_approvals_route(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ,
            {
                "AI_OS_RUNTIME_MODE": "staging",
                "AI_OS_IDENTITY_SIGNING_SECRET": "s21-composition-test-secret-123",
                "AI_OS_TLS_TERMINATED_BY_EDGE": "true",
            },
            clear=False,
        ):
            server, entrypoint, identity = build_s21_http_server(
                port=0,
                tls_terminated=True,
                persistence_root=Path(td) / "runtime",
            )
            try:
                token = identity.issue_token("operator-01")["token"]
                server.start()
                host, port = server.address
                conn = HTTPConnection(host, port, timeout=5)
                conn.request(
                    "GET",
                    "/api/approvals",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response = conn.getresponse()
                body = json.loads(response.read().decode("utf-8"))
                conn.close()

                self.assertEqual(response.status, 200)
                self.assertEqual(body["status"], "ADMITTED")
                self.assertEqual(body["application_response"]["status"], "OK")
                self.assertEqual(body["application_response"]["approvals"], [])
                self.assertFalse(body["external_action_executed"])
                self.assertFalse(body["memory_write_executed"])

                registered = entrypoint.runtime._ensure_o45()[1].list()
                tools_by_name = {item["tool_name"]: item for item in registered}
                self.assertIn("provider.search.live", tools_by_name)
                self.assertIn("provider.research.live", tools_by_name)
                self.assertIn("provider.research.synthesis", tools_by_name)
                self.assertIn("provider.research.workflow", tools_by_name)
                self.assertIn("provider.project.plan", tools_by_name)
                self.assertFalse(tools_by_name["provider.research.live"]["retry_safe"])
                self.assertFalse(tools_by_name["provider.research.synthesis"]["retry_safe"])
                self.assertFalse(tools_by_name["provider.research.workflow"]["retry_safe"])
                self.assertFalse(tools_by_name["provider.project.plan"]["retry_safe"])
            finally:
                server.shutdown()
                entrypoint.close()

    def test_invalid_signed_bearer_is_rejected_before_canonical_route(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ,
            {
                "AI_OS_RUNTIME_MODE": "staging",
                "AI_OS_IDENTITY_SIGNING_SECRET": "s21-composition-test-secret-456",
                "AI_OS_TLS_TERMINATED_BY_EDGE": "true",
            },
            clear=False,
        ):
            server, entrypoint, _identity = build_s21_http_server(
                port=0,
                tls_terminated=True,
                persistence_root=Path(td) / "runtime",
            )
            try:
                server.start()
                host, port = server.address
                conn = HTTPConnection(host, port, timeout=5)
                conn.request(
                    "GET",
                    "/api/approvals",
                    headers={"Authorization": "Bearer definitely-invalid"},
                )
                response = conn.getresponse()
                body = json.loads(response.read().decode("utf-8"))
                conn.close()

                self.assertEqual(response.status, 401)
                self.assertIn("authenticated", body["failures"])
                self.assertNotIn("application_response", body)
            finally:
                server.shutdown()
                entrypoint.close()


if __name__ == "__main__":
    unittest.main()
