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


class TestS21HTTPWorkspaceReadAPI(unittest.TestCase):
    """Verify owner-scoped workspace read/list/review over the authenticated HTTP surface."""

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

    def test_list_read_review_are_authenticated_owner_scoped_and_read_only(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ,
            {
                "AI_OS_RUNTIME_MODE": "staging",
                "AI_OS_IDENTITY_SIGNING_SECRET": "patch29-http-test-signing-secret",
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
                    "run_id": "PATCH29-HTTP-SUBMIT",
                    "project_id": PROJECT_ID,
                    "strategy_id": "PATCH29-HTTP-STRATEGY",
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
                    server.address, "POST", "/api/runs", operator_token, submission
                )
                self.assertEqual(code, 200, msg=repr(submitted))
                intent = submitted["application_response"]["governed_execution"]["intent"]["intent_id"]

                code, executed = self._request(
                    server.address,
                    "POST",
                    f"/api/intents/{intent}/execute",
                    operator_token,
                    {},
                )
                self.assertEqual(code, 200, msg=repr(executed))
                self.assertEqual(executed["application_response"]["status"], "SUCCEEDED")

                code, listing = self._request(
                    server.address, "GET", "/api/projects?limit=10", operator_token
                )
                self.assertEqual(code, 200, msg=repr(listing))
                list_result = listing["application_response"]
                self.assertEqual(list_result["status"], "OK")
                self.assertEqual(list_result["count"], 1)
                self.assertEqual(list_result["projects"][0]["project_id"], PROJECT_ID)
                self.assertEqual(list_result["projects"][0]["task_tracking"]["task_count"], 4)

                code, detail = self._request(
                    server.address, "GET", f"/api/projects/{PROJECT_ID}", operator_token
                )
                self.assertEqual(code, 200, msg=repr(detail))
                detail_result = detail["application_response"]
                self.assertEqual(detail_result["status"], "OK")
                self.assertEqual(detail_result["workspace"]["owner_id"], "operator-01")
                self.assertFalse(detail_result["workspace"]["external_actions_executed"])

                code, review = self._request(
                    server.address, "GET", f"/api/projects/{PROJECT_ID}/review", operator_token
                )
                self.assertEqual(code, 200, msg=repr(review))
                review_result = review["application_response"]
                self.assertEqual(review_result["status"], "OK")
                self.assertEqual(review_result["review_type"], "DETERMINISTIC_READ_ONLY")
                self.assertEqual(review_result["project_status"], "ACTIVE")
                self.assertEqual(review_result["task_tracking"]["task_count"], 4)
                self.assertFalse(review_result["workspace_mutated"])
                self.assertFalse(review_result["external_actions_executed"])

                # A valid but different authenticated identity sees the same not-found
                # response as for an absent project; ownership is never caller-selectable.
                code, hidden = self._request(
                    server.address, "GET", f"/api/projects/{PROJECT_ID}", viewer_token
                )
                self.assertEqual(code, 404, msg=repr(hidden))
                self.assertEqual(hidden["application_response"]["status"], "NOT_FOUND")
                self.assertEqual(
                    hidden["application_response"]["reason"],
                    "project_workspace_not_found",
                )

                # The read/list/review requests do not repeat any model/search work.
                search.assert_called_once()
                synthesis_model.assert_called_once()
                plan_model.assert_called_once()
            finally:
                server.shutdown()
                entrypoint.close()

    def test_project_list_rejects_invalid_limit(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ,
            {
                "AI_OS_RUNTIME_MODE": "staging",
                "AI_OS_IDENTITY_SIGNING_SECRET": "patch29-http-test-signing-secret",
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
                token_result = identity.issue_token("operator-01")
                code, result = self._request(
                    server.address, "GET", "/api/projects?limit=1000",
                    token_result["token"],
                )
                self.assertEqual(code, 400, msg=repr(result))
                self.assertEqual(result["application_response"]["status"], "BAD_REQUEST")
                self.assertEqual(
                    result["application_response"]["reason"],
                    "project_limit_out_of_range",
                )
            finally:
                server.shutdown()
                entrypoint.close()


if __name__ == "__main__":
    unittest.main()
