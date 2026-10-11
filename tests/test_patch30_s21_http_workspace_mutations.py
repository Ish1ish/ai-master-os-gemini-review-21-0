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


class TestS21HTTPWorkspaceMutations(unittest.TestCase):
    """Verify workspace changes are owner-scoped and explicitly O45-driven."""

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

    def _submit_and_execute(self, address, token, project_id, route, body):
        code, submitted = self._request(address, "POST", route, token, body)
        self.assertEqual(code, 200, msg=repr(submitted))
        app = submitted["application_response"]
        self.assertEqual(app["status"], "PASS", msg=repr(app))
        governed = app["governed_execution"]
        self.assertEqual(governed["status"], "READY", msg=repr(governed))
        intent_id = governed["intent"]["intent_id"]
        # Submission is deliberately non-mutating. The only write happens after
        # the caller explicitly drives the returned governed intent.
        before = self._request(
            address, "GET", f"/api/projects/{project_id}", token
        )[1]["application_response"]["workspace"]
        self.assertEqual(before["revision"], body["expected_revision"])
        code, executed = self._request(
            address,
            "POST",
            f"/api/intents/{intent_id}/execute",
            token,
            {},
        )
        self.assertEqual(code, 200, msg=repr(executed))
        self.assertEqual(
            executed["application_response"]["status"], "SUCCEEDED",
            msg=repr(executed),
        )
        return executed

    def test_task_note_and_decision_changes_require_explicit_governed_execute(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ,
            {
                "AI_OS_RUNTIME_MODE": "staging",
                "AI_OS_IDENTITY_SIGNING_SECRET": "patch30-http-test-signing-secret",
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
                operator = identity.issue_token("operator-01")
                viewer = identity.issue_token("viewer-01")
                self.assertEqual(operator["status"], "ISSUED")
                self.assertEqual(viewer["status"], "ISSUED")
                operator_token = operator["token"]
                viewer_token = viewer["token"]

                submission = {
                    "run_id": "PATCH30-HTTP-CREATE",
                    "project_id": PROJECT_ID,
                    "strategy_id": "PATCH30-HTTP-CREATE-STRATEGY",
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
                code, created = self._request(
                    server.address, "POST", "/api/runs", operator_token, submission
                )
                self.assertEqual(code, 200, msg=repr(created))
                intent_id = created["application_response"]["governed_execution"]["intent"]["intent_id"]
                code, executed = self._request(
                    server.address, "POST", f"/api/intents/{intent_id}/execute",
                    operator_token, {},
                )
                self.assertEqual(code, 200, msg=repr(executed))
                self.assertEqual(executed["application_response"]["status"], "SUCCEEDED")

                # The viewer has no run:submit capability and cannot stage writes.
                code, denied = self._request(
                    server.address,
                    "POST",
                    f"/api/projects/{PROJECT_ID}/tasks/M01-T01",
                    viewer_token,
                    {"expected_revision": 1, "task_status": "DONE"},
                )
                self.assertEqual(code, 403, msg=repr(denied))
                self.assertEqual(denied["application_response"]["status"], "FORBIDDEN")

                # Tasks are changed through an explicit governed intent.
                self._submit_and_execute(
                    server.address, operator_token, PROJECT_ID,
                    f"/api/projects/{PROJECT_ID}/tasks/M01-T01",
                    {
                        "expected_revision": 1,
                        "task_status": "IN_PROGRESS",
                        "note": "Interview recruiting started.",
                        "requested_by": "viewer-01",
                    },
                )
                saved = self._request(
                    server.address, "GET", f"/api/projects/{PROJECT_ID}", operator_token
                )[1]["application_response"]["workspace"]
                self.assertEqual(saved["revision"], 2)
                task = next(item for item in saved["tasks"] if item["task_id"] == "M01-T01")
                self.assertEqual(task["status"], "IN_PROGRESS")
                self.assertEqual(task["note"], "Interview recruiting started.")

                # Body-supplied author/requested_by must never override the identity.
                self._submit_and_execute(
                    server.address, operator_token, PROJECT_ID,
                    f"/api/projects/{PROJECT_ID}/notes",
                    {
                        "expected_revision": 2,
                        "note": "The supplier quote is still pending.",
                        "note_type": "blocker",
                        "author": "viewer-01",
                        "requested_by": "viewer-01",
                    },
                )
                saved = self._request(
                    server.address, "GET", f"/api/projects/{PROJECT_ID}", operator_token
                )[1]["application_response"]["workspace"]
                self.assertEqual(saved["revision"], 3)
                self.assertEqual(saved["notes"][-1]["author"], "operator-01")
                self.assertEqual(saved["notes"][-1]["note_type"], "blocker")

                self._submit_and_execute(
                    server.address, operator_token, PROJECT_ID,
                    f"/api/projects/{PROJECT_ID}/decisions",
                    {
                        "expected_revision": 3,
                        "title": "Validate demand before scaling",
                        "rationale": "Search snippets alone do not demonstrate willingness to pay.",
                        "source_ids": ["S001"],
                        "author": "viewer-01",
                        "requested_by": "viewer-01",
                    },
                )
                saved = self._request(
                    server.address, "GET", f"/api/projects/{PROJECT_ID}", operator_token
                )[1]["application_response"]["workspace"]
                self.assertEqual(saved["revision"], 4)
                self.assertEqual(saved["decisions"][-1]["author"], "operator-01")
                self.assertEqual(saved["decisions"][-1]["source_ids"], ["S001"])
                self.assertFalse(saved["external_actions_executed"])

                # Stale revisions are rejected before a governed intent is created.
                code, stale = self._request(
                    server.address,
                    "POST",
                    f"/api/projects/{PROJECT_ID}/tasks/M01-T02",
                    operator_token,
                    {"expected_revision": 1, "task_status": "DONE"},
                )
                self.assertEqual(code, 409, msg=repr(stale))
                self.assertEqual(
                    stale["application_response"]["reason"],
                    "project_workspace_revision_mismatch",
                )
                search.assert_called_once()
                synthesis_model.assert_called_once()
                plan_model.assert_called_once()
            finally:
                server.shutdown()
                entrypoint.close()

    def test_mutation_cannot_target_another_owners_project(self):
        # The owner check happens before revision disclosure or intent submission.
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ,
            {
                "AI_OS_RUNTIME_MODE": "staging",
                "AI_OS_IDENTITY_SIGNING_SECRET": "patch30-http-test-signing-secret",
                "AI_OS_TLS_TERMINATED_BY_EDGE": "true",
            },
            clear=False,
        ):
            server, entrypoint, identity = build_s21_http_server(
                port=0,
                tls_terminated=True,
                persistence_root=Path(td) / "runtime",
            )
            server.start()
            try:
                viewer = identity.issue_token("viewer-01")
                code, result = self._request(
                    server.address,
                    "POST",
                    "/api/projects/NOT-OWNED/notes",
                    viewer["token"],
                    {"expected_revision": 1, "note": "Should not be accepted."},
                )
                self.assertEqual(code, 403, msg=repr(result))
                self.assertEqual(result["application_response"]["status"], "FORBIDDEN")
            finally:
                server.shutdown()
                entrypoint.close()


if __name__ == "__main__":
    unittest.main()
