from __future__ import annotations

import json
import os
import tempfile
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

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


class TestS21HTTPAddProjectTask(unittest.TestCase):
    """New tasks are audited, revisioned and only saved after explicit O45 drive."""

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

    def _execute_submitted_intent(self, address, token, project_id, route, body):
        code, submitted = self._request(address, "POST", route, token, body)
        self.assertEqual(code, 200, msg=repr(submitted))
        application = submitted["application_response"]
        self.assertEqual(application["status"], "PASS", msg=repr(application))
        governed = application["governed_execution"]
        self.assertEqual(governed["status"], "READY", msg=repr(governed))
        # A submit-only request must not mutate the persistent project yet.
        code, detail = self._request(
            address, "GET", f"/api/projects/{project_id}", token
        )
        self.assertEqual(code, 200, msg=repr(detail))
        self.assertEqual(
            detail["application_response"]["workspace"]["revision"],
            body["expected_revision"],
        )
        code, executed = self._request(
            address,
            "POST",
            f"/api/intents/{governed['intent']['intent_id']}/execute",
            token,
            {},
        )
        self.assertEqual(code, 200, msg=repr(executed))
        self.assertEqual(
            executed["application_response"]["status"], "SUCCEEDED",
            msg=repr(executed),
        )
        return executed

    def test_add_task_is_governed_audited_and_respects_pause_and_validation(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ,
            {
                "AI_OS_RUNTIME_MODE": "staging",
                "AI_OS_IDENTITY_SIGNING_SECRET": "patch32-http-test-signing-secret",
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

            server, entrypoint, identity = build_s21_http_server(
                port=0,
                tls_terminated=True,
                persistence_root=Path(td) / "runtime",
            )
            server.start()
            try:
                issued = identity.issue_token("operator-01")
                self.assertEqual(issued["status"], "ISSUED")
                token = issued["token"]

                create_payload = {
                    "run_id": "PATCH32-HTTP-CREATE",
                    "project_id": PROJECT_ID,
                    "strategy_id": "PATCH32-HTTP-CREATE-STRATEGY",
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
                code, submitted = self._request(
                    server.address, "POST", "/api/runs", token, create_payload
                )
                self.assertEqual(code, 200, msg=repr(submitted))
                intent_id = submitted["application_response"]["governed_execution"]["intent"]["intent_id"]
                code, created = self._request(
                    server.address, "POST", f"/api/intents/{intent_id}/execute", token, {}
                )
                self.assertEqual(code, 200, msg=repr(created))
                self.assertEqual(created["application_response"]["status"], "SUCCEEDED")

                detail_path = f"/api/projects/{PROJECT_ID}"
                code, initial_response = self._request(
                    server.address, "GET", detail_path, token
                )
                self.assertEqual(code, 200, msg=repr(initial_response))
                initial = initial_response["application_response"]["workspace"]
                self.assertEqual(initial["revision"], 1)
                self.assertEqual(initial["task_tracking"]["task_count"], 4)

                # Additional work discovered after planning can be added to a milestone.
                self._execute_submitted_intent(
                    server.address, token, PROJECT_ID,
                    f"/api/projects/{PROJECT_ID}/tasks",
                    {
                        "expected_revision": 1,
                        "title": "Confirm supplier lead times",
                        "note": "Ask two suppliers for delivery estimates.",
                        "priority": "high",
                        "due_in_days": 4,
                        "success_criteria": "Two written delivery estimates are recorded.",
                        "milestone_id": "M01",
                        "requested_by": "viewer-01",
                        "author": "viewer-01",
                    },
                )
                code, after_response = self._request(
                    server.address, "GET", detail_path, token
                )
                self.assertEqual(code, 200, msg=repr(after_response))
                detail = after_response["application_response"]
                workspace = detail["workspace"]
                self.assertEqual(workspace["revision"], 2)
                self.assertEqual(workspace["task_tracking"]["task_count"], 5)
                task = next(item for item in workspace["tasks"] if item["task_id"] == "X001")
                self.assertEqual(task["task_type"], "ad_hoc")
                self.assertEqual(task["title"], "Confirm supplier lead times")
                self.assertEqual(task["status"], "TODO")
                self.assertEqual(task["note"], "Ask two suppliers for delivery estimates.")
                self.assertEqual(task["priority"], "high")
                self.assertEqual(task["due_in_days"], 4)
                self.assertEqual(task["milestone_id"], "M01")
                self.assertEqual(task["milestone_name"], "Demand validation")
                self.assertEqual(
                    task["success_criteria"],
                    "Two written delivery estimates are recorded.",
                )
                first_milestone = workspace["milestone_tracking"]["milestones"][0]
                self.assertEqual(first_milestone["task_tracking"]["task_count"], 3)
                self.assertEqual(workspace["events"][-1]["event_type"], "ADD_TASK")
                self.assertEqual(workspace["events"][-1]["payload"]["author"], "operator-01")
                self.assertFalse(workspace["external_actions_executed"])

                # A paused workspace cannot accept a new task.
                self._execute_submitted_intent(
                    server.address, token, PROJECT_ID,
                    f"/api/projects/{PROJECT_ID}/status",
                    {"expected_revision": 2, "project_status": "PAUSED"},
                )
                code, paused = self._request(
                    server.address, "POST", f"/api/projects/{PROJECT_ID}/tasks", token,
                    {
                        "expected_revision": 3,
                        "title": "Blocked while paused",
                    },
                )
                self.assertEqual(code, 409, msg=repr(paused))
                self.assertEqual(
                    paused["application_response"]["reason"],
                    "project_workspace_paused",
                )

                # Resume and verify malformed optional metadata is rejected pre-submit.
                self._execute_submitted_intent(
                    server.address, token, PROJECT_ID,
                    f"/api/projects/{PROJECT_ID}/status",
                    {"expected_revision": 3, "project_status": "ACTIVE"},
                )
                code, invalid = self._request(
                    server.address, "POST", f"/api/projects/{PROJECT_ID}/tasks", token,
                    {
                        "expected_revision": 4,
                        "title": "Invalid priority task",
                        "priority": "highest-ever",
                    },
                )
                self.assertEqual(code, 400, msg=repr(invalid))
                self.assertEqual(
                    invalid["application_response"]["reason"],
                    "project_workspace_task_priority_invalid",
                )

                final_detail = self._request(
                    server.address, "GET", detail_path, token
                )[1]["application_response"]["workspace"]
                self.assertEqual(final_detail["revision"], 4)
                self.assertEqual(final_detail["task_tracking"]["task_count"], 5)
                search.assert_called_once()
                synthesis_model.assert_called_once()
                plan_model.assert_called_once()
            finally:
                server.shutdown()
                entrypoint.close()


if __name__ == "__main__":
    unittest.main()
