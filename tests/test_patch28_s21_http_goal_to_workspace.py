from __future__ import annotations

import json
import os
import tempfile
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

from core.src.project_workspace_store import ProjectWorkspaceStore
from unified_runtime.s21_http_launcher import build_s21_http_server
from test_patch27_live_goal_to_workspace import (
    AUDIENCE,
    CONSTRAINTS,
    GOAL,
    PROJECT_ID,
    _PLAN_OUTPUT,
    _SYNTHESIS_OUTPUT,
    _model_response,
)


class TestS21HTTPGoalToWorkspaceEndToEnd(unittest.TestCase):
    """Exercise auth -> S21 HTTP -> O45 submit -> explicit HTTP execute -> SQLite."""

    def _request(self, address, method, path, token, body=None):
        host, port = address
        connection = HTTPConnection(host, port, timeout=12)
        encoded = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {token}"}
        if encoded is not None:
            headers["Content-Type"] = "application/json"
        connection.request(method, path, body=encoded, headers=headers)
        response = connection.getresponse()
        raw = response.read().decode("utf-8")
        connection.close()
        return response.status, json.loads(raw) if raw else {}

    def test_signed_http_request_submits_then_explicitly_executes_full_pipeline(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ,
            {
                "AI_OS_RUNTIME_MODE": "staging",
                "AI_OS_IDENTITY_SIGNING_SECRET": "patch28-http-test-signing-secret",
                "AI_OS_TLS_TERMINATED_BY_EDGE": "true",
            },
            clear=False,
        ), patch("core.src.canonical_provider_tools.search_provider") as search, patch(
            "core.src.research_synthesis.model_provider"
        ) as synthesis_model, patch(
            "core.src.project_plan_generator.model_provider"
        ) as plan_model:
            search.return_value = {
                "results": [{
                    "url": "https://example.com/market",
                    "title": "Prepared meal services overview",
                    "snippet": "A search-result snippet describing prepared meal services.",
                }]
            }
            synthesis_model.return_value = _model_response(_SYNTHESIS_OUTPUT)
            plan_model.return_value = _model_response(_PLAN_OUTPUT)

            root = Path(td) / "runtime"
            server, entrypoint, identity = build_s21_http_server(
                port=0,
                tls_terminated=True,
                persistence_root=root,
            )
            server.start()
            try:
                token_result = identity.issue_token("operator-01")
                self.assertEqual(token_result["status"], "ISSUED")
                token = token_result["token"]

                store = ProjectWorkspaceStore(root / "project_workspace.sqlite3")
                submission_payload = {
                    "run_id": "PATCH28-HTTP-SUBMIT",
                    "project_id": PROJECT_ID,
                    "strategy_id": "PATCH28-HTTP-STRATEGY",
                    "intent": "Research the market, prepare a project plan, and save it",
                    "goal": GOAL,
                    "audience": AUDIENCE,
                    "constraints": CONSTRAINTS,
                    "requested_language": "en",
                    "execution_contract": {
                        "action": "update_project_workspace",
                        "tool_name": "provider.project.goal-to-workspace",
                        "payload": {
                            "project_id": PROJECT_ID,
                            "goal": GOAL,
                            "audience": AUDIENCE,
                            "constraints": CONSTRAINTS,
                            "requested_language": "en",
                            "max_queries": 1,
                        },
                    },
                }

                status_code, submitted = self._request(
                    server.address, "POST", "/api/runs", token, submission_payload
                )
                self.assertEqual(status_code, 200, msg=repr(submitted))
                self.assertEqual(submitted["status"], "ADMITTED")
                application = submitted["application_response"]
                self.assertEqual(application["status"], "PASS")
                governed = application["governed_execution"]
                self.assertEqual(governed["status"], "READY")

                # Even through the live HTTP surface, submit-only stays submit-only.
                search.assert_not_called()
                synthesis_model.assert_not_called()
                plan_model.assert_not_called()
                absent = store.read({
                    "operation": "get",
                    "project_id": PROJECT_ID,
                    "requested_by": "operator-01",
                })
                self.assertEqual(absent["status"], "NOT_FOUND")

                intent_id = governed["intent"]["intent_id"]
                status_code, executed = self._request(
                    server.address,
                    "POST",
                    f"/api/intents/{intent_id}/execute",
                    token,
                    {},
                )
                self.assertEqual(status_code, 200, msg=repr(executed))
                self.assertEqual(executed["status"], "ADMITTED")
                execution_result = executed["application_response"]
                self.assertEqual(
                    execution_result["status"], "SUCCEEDED",
                    msg=repr(execution_result),
                )

                search.assert_called_once()
                synthesis_model.assert_called_once()
                plan_model.assert_called_once()
                saved = store.read({
                    "operation": "get",
                    "project_id": PROJECT_ID,
                    "requested_by": "operator-01",
                })
                self.assertEqual(saved["status"], "OK")
                workspace = saved["workspace"]
                self.assertEqual(workspace["owner_id"], "operator-01")
                self.assertEqual(workspace["project_id"], PROJECT_ID)
                self.assertEqual(workspace["status"], "ACTIVE")
                self.assertEqual(workspace["sources"][0]["source_id"], "S001")
                self.assertEqual(workspace["sources"][0]["url"], "https://example.com/market")
                self.assertEqual(workspace["research_status"], "COMPLETE")
                self.assertEqual(workspace["task_tracking"]["task_count"], 4)
                self.assertFalse(workspace["decision_grade_evidence"])
                self.assertFalse(workspace["external_actions_executed"])
                self.assertFalse(executed["external_action_executed"])
                self.assertFalse(executed["memory_write_executed"])
            finally:
                server.shutdown()
                entrypoint.close()


if __name__ == "__main__":
    unittest.main()
