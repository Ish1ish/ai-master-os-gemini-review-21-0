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


class TestS21HTTPProjectLifecycle(unittest.TestCase):
    """Project status changes are owner-scoped O45 intents, not direct HTTP writes."""

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

    def _submit_and_execute(self, address, token, route, body):
        code, submitted = self._request(address, "POST", route, token, body)
        self.assertEqual(code, 200, msg=repr(submitted))
        app = submitted["application_response"]
        self.assertEqual(app["status"], "PASS", msg=repr(app))
        governed = app["governed_execution"]
        self.assertEqual(governed["status"], "READY", msg=repr(governed))
        code, executed = self._request(
            address, "POST",
            f"/api/intents/{governed['intent']['intent_id']}/execute",
            token, {},
        )
        self.assertEqual(code, 200, msg=repr(executed))
        self.assertEqual(
            executed["application_response"]["status"], "SUCCEEDED",
            msg=repr(executed),
        )
        return executed

    def test_pause_resume_completion_and_archive_use_governed_status_updates(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ,
            {
                "AI_OS_RUNTIME_MODE": "staging",
                "AI_OS_IDENTITY_SIGNING_SECRET": "patch31-http-test-signing-secret",
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

                creation = {
                    "run_id": "PATCH31-HTTP-CREATE",
                    "project_id": PROJECT_ID,
                    "strategy_id": "PATCH31-HTTP-CREATE-STRATEGY",
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
                    server.address, "POST", "/api/runs", token, creation
                )
                self.assertEqual(code, 200, msg=repr(submitted))
                intent_id = submitted["application_response"]["governed_execution"]["intent"]["intent_id"]
                code, executed = self._request(
                    server.address, "POST", f"/api/intents/{intent_id}/execute", token, {}
                )
                self.assertEqual(code, 200, msg=repr(executed))
                self.assertEqual(executed["application_response"]["status"], "SUCCEEDED")

                route = f"/api/projects/{PROJECT_ID}/status"
                paused = self._submit_and_execute(
                    server.address, token, route,
                    {"expected_revision": 1, "project_status": "PAUSED"},
                )
                detail = self._request(
                    server.address, "GET", f"/api/projects/{PROJECT_ID}", token
                )[1]["application_response"]
                self.assertEqual(detail["workspace"]["status"], "PAUSED")
                self.assertEqual(detail["workspace"]["revision"], 2)

                code, paused_task = self._request(
                    server.address, "POST",
                    f"/api/projects/{PROJECT_ID}/tasks/M01-T01", token,
                    {"expected_revision": 2, "task_status": "IN_PROGRESS"},
                )
                self.assertEqual(code, 409, msg=repr(paused_task))
                self.assertEqual(
                    paused_task["application_response"]["reason"],
                    "project_workspace_paused",
                )

                code, unchanged = self._request(
                    server.address, "POST", route, token,
                    {"expected_revision": 2, "project_status": "PAUSED"},
                )
                self.assertEqual(code, 400, msg=repr(unchanged))
                self.assertEqual(
                    unchanged["application_response"]["reason"],
                    "project_workspace_status_unchanged",
                )

                resumed = self._submit_and_execute(
                    server.address, token, route,
                    {"expected_revision": 2, "project_status": "ACTIVE"},
                )
                detail = self._request(
                    server.address, "GET", f"/api/projects/{PROJECT_ID}", token
                )[1]["application_response"]
                self.assertEqual(detail["workspace"]["status"], "ACTIVE")
                self.assertEqual(detail["workspace"]["revision"], 3)

                code, invalid = self._request(
                    server.address, "POST", route, token,
                    {"expected_revision": 3, "project_status": "ERASED"},
                )
                self.assertEqual(code, 400, msg=repr(invalid))
                self.assertEqual(
                    invalid["application_response"]["reason"],
                    "project_workspace_status_invalid",
                )

                code, incomplete = self._request(
                    server.address, "POST", route, token,
                    {"expected_revision": 3, "project_status": "COMPLETED"},
                )
                self.assertEqual(code, 409, msg=repr(incomplete))
                self.assertEqual(
                    incomplete["application_response"]["reason"],
                    "project_completion_requires_all_tasks_resolved",
                )
                self.assertEqual(
                    incomplete["application_response"]["unfinished_task_count"], 4
                )

                # Prepare the completion fixture through the same durable store.
                # The API-level task mutation path is covered by PATCH30's focused tests.
                store = entrypoint.project_workspace_store
                revision = 3
                detail = store.read({
                    "operation": "get",
                    "project_id": PROJECT_ID,
                    "requested_by": "operator-01",
                })
                for task in detail["workspace"]["tasks"]:
                    marked = store.write({
                        "operation": "update_task",
                        "project_id": PROJECT_ID,
                        "requested_by": "operator-01",
                        "expected_revision": revision,
                        "task_id": task["task_id"],
                        "task_status": "DONE",
                    })
                    self.assertEqual(marked["status"], "UPDATED", msg=repr(marked))
                    revision = marked["revision"]

                completed = self._submit_and_execute(
                    server.address, token, route,
                    {"expected_revision": revision, "project_status": "COMPLETED"},
                )
                detail = self._request(
                    server.address, "GET", f"/api/projects/{PROJECT_ID}", token
                )[1]["application_response"]
                self.assertEqual(detail["workspace"]["status"], "COMPLETED")
                completed_revision = detail["workspace"]["revision"]

                code, no_reopen = self._request(
                    server.address, "POST", route, token,
                    {"expected_revision": completed_revision, "project_status": "ACTIVE"},
                )
                self.assertEqual(code, 409, msg=repr(no_reopen))
                self.assertEqual(
                    no_reopen["application_response"]["reason"],
                    "project_workspace_completed",
                )

                self._submit_and_execute(
                    server.address, token, route,
                    {"expected_revision": completed_revision, "project_status": "ARCHIVED"},
                )
                detail = self._request(
                    server.address, "GET", f"/api/projects/{PROJECT_ID}", token
                )[1]["application_response"]
                self.assertEqual(detail["workspace"]["status"], "ARCHIVED")
                self.assertEqual(detail["workspace"]["revision"], completed_revision + 1)

                code, archived_update = self._request(
                    server.address, "POST", route, token,
                    {
                        "expected_revision": completed_revision + 1,
                        "project_status": "ACTIVE",
                    },
                )
                self.assertEqual(code, 409, msg=repr(archived_update))
                self.assertEqual(
                    archived_update["application_response"]["reason"],
                    "project_workspace_archived",
                )
                search.assert_called_once()
                synthesis_model.assert_called_once()
                plan_model.assert_called_once()
            finally:
                server.shutdown()
                entrypoint.close()


if __name__ == "__main__":
    unittest.main()
