from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from unified_runtime.s21_http_launcher import build_s21_http_server


class TestPatch12S21WorkerExecutionBoundary(unittest.TestCase):
    def test_operator_execute_delegates_to_internal_worker(self):
        with patch.dict(
            os.environ,
            {
                "AI_OS_RUNTIME_MODE": "staging",
                "AI_OS_IDENTITY_SIGNING_SECRET": "aios-local-staging-secret-2026-strong",
            },
            clear=False,
        ):
            with tempfile.TemporaryDirectory() as root:
                server, entrypoint, identity = build_s21_http_server(
                    port=0,
                    tls_terminated=True,
                    persistence_root=root,
                )
                try:
                    entrypoint.register_execution_tool(
                        "internal.echo",
                        lambda payload: {
                            "status": "SUCCEEDED",
                            "output": {"value": payload.get("value")},
                        },
                        version="1.0.0",
                    )

                    self.assertEqual(
                        entrypoint.execution_principal["principal"],
                        "worker-01",
                    )
                    self.assertIn(
                        "job:execute",
                        entrypoint.execution_principal["scopes"],
                    )

                    token = identity.issue_token("operator-01")["token"]
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    }

                    submit = server.handle_http(
                        method="POST",
                        path="/api/runs",
                        headers=headers,
                        body={
                            "run_id": "PATCH12-WORKER-001",
                            "project_id": "PATCH12-WORKER",
                            "strategy_id": "PATCH12-WORKER",
                            "intent": "Verify worker execution boundary",
                            "execution_contract": {
                                "action": "read_only_inspection",
                                "tool_name": "internal.echo",
                                "payload": {"value": "patch12"},
                                "context": {
                                    "confidence": "high",
                                    "evidence_refs": ["PATCH12-1"],
                                    "evidence_boundary": "local_evidence_supported",
                                },
                            },
                        },
                    )
                    self.assertEqual(submit.status_code, 200)
                    app = submit.body["application_response"]
                    execution = app["governed_execution"]["submission"]["execution"]
                    intent_id = app["governed_execution"]["intent"]["intent_id"]
                    self.assertEqual(execution["state"], "READY")
                    self.assertEqual(execution["requested_by"], "operator-01")

                    driven = server.handle_http(
                        method="POST",
                        path=f"/api/intents/{intent_id}/execute",
                        headers=headers,
                        body={},
                    )
                    self.assertEqual(driven.status_code, 200)
                    result = driven.body["application_response"]
                    self.assertEqual(result["status"], "SUCCEEDED")
                    self.assertEqual(result["execution"]["state"], "SUCCEEDED")
                    self.assertEqual(
                        result["execution"]["result"]["output"]["value"],
                        "patch12",
                    )
                finally:
                    # This test uses handle_http() directly and never starts
                    # serve_forever(); calling HTTPServer.shutdown() here would
                    # wait forever for a non-running serve_forever loop.
                    server._server.server_close()
                    entrypoint.close()


if __name__ == "__main__":
    unittest.main()
