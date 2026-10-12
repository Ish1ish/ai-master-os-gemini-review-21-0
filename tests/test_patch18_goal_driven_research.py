from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from unified_runtime.integrated_runtime import RealUnifiedRuntime

from core.src.canonical_provider_tools import (
    MAX_RESEARCH_QUERIES,
    build_research_queries,
    real_research_tool,
)


class TestPatch18GoalDrivenResearchQueries(unittest.TestCase):
    def test_queries_are_deterministic_and_bounded(self):
        args = (
            "Start a home cooking business",
            "busy office workers",
            {"location": "Alexandria, Egypt", "budget": {"amount": 10000, "currency": "EGP"}},
        )
        first = build_research_queries(*args)
        second = build_research_queries(*args)

        self.assertEqual(first, second)
        self.assertLessEqual(len(first), MAX_RESEARCH_QUERIES)
        self.assertIn("Alexandria, Egypt", " ".join(first))
        self.assertIn("busy office workers", " ".join(first))
        self.assertIn("10000 EGP", " ".join(first))

    def test_location_is_not_assumed_and_changes_queries(self):
        goal = "Launch an online bakery"
        without_location = build_research_queries(goal, "local families", {})
        with_location = build_research_queries(
            goal, "local families", {"location": "Giza, Egypt"}
        )

        self.assertNotEqual(without_location, with_location)
        self.assertNotIn("Egypt", " ".join(without_location))
        self.assertIn("Giza, Egypt", " ".join(with_location))

    def test_only_allowlisted_constraint_fields_enter_queries(self):
        queries = build_research_queries(
            "Sell handmade candles",
            "gift buyers",
            {
                "location": "Cairo",
                "private_notes": "DO-NOT-LEAK-THIS",
                "access_token": "DO-NOT-LEAK-THIS-EITHER",
            },
        )
        text = " ".join(queries)
        self.assertIn("Cairo", text)
        self.assertNotIn("DO-NOT-LEAK-THIS", text)

    def test_blank_goal_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "goal_required"):
            build_research_queries("  ")


class TestPatch18GoalDrivenResearchExecution(unittest.TestCase):
    def test_normalizes_sources_deduplicates_urls_and_records_provenance(self):
        calls = []

        def fake_search(query):
            calls.append(query)
            return {
                "results": [
                    {
                        "title": " Market Report ",
                        "url": "https://example.com/report#section",
                        "content": "Demand is increasing. ",
                        "published_date": "2026-09-01",
                    },
                    {
                        "title": "Duplicate",
                        "link": "https://example.com/report#other",
                        "snippet": "Duplicate URL",
                    },
                    {
                        "title": "Bad scheme",
                        "url": "javascript:alert(1)",
                        "snippet": "must be ignored",
                    },
                ]
            }

        with patch("core.src.canonical_provider_tools.search_provider", side_effect=fake_search):
            result = real_research_tool({
                "goal": "Test demand for affordable meal prep",
                "audience": "students",
                "constraints": {"location": "Cairo"},
                "max_queries": 2,
            })

        self.assertEqual(len(calls), 2)
        self.assertEqual(result["query_count"], 2)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["result_count"], 1)
        source = result["results"][0]
        self.assertEqual(source["url"], "https://example.com/report")
        self.assertEqual(source["title"], "Market Report")
        self.assertEqual(source["snippet"], "Demand is increasing.")
        self.assertEqual(source["published_at"], "2026-09-01")
        self.assertEqual(len(source["matched_queries"]), 2)
        self.assertTrue(source["accessed_at"].endswith("Z"))
        self.assertNotIn("javascript:", str(result))

    def test_partial_provider_failure_is_visible_when_other_sources_succeed(self):
        call_count = 0

        def mixed_search(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("private provider diagnostic")
            return {
                "results": [{
                    "title": "Useful source",
                    "url": "https://example.org/source",
                    "snippet": "Relevant data",
                }]
            }

        with patch("core.src.canonical_provider_tools.search_provider", side_effect=mixed_search):
            result = real_research_tool({"goal": "Validate handmade soap demand", "max_queries": 2})

        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["result_count"], 1)
        self.assertEqual(result["query_statuses"][0]["status"], "FAILED")
        self.assertEqual(result["query_statuses"][0]["reason"], "provider_query_failed")
        self.assertNotIn("private provider diagnostic", str(result))

    def test_no_citable_sources_fails_with_safe_error(self):
        with patch(
            "core.src.canonical_provider_tools.search_provider",
            return_value={"results": [{"title": "No URL", "snippet": "No citation"}]},
        ):
            with self.assertRaisesRegex(RuntimeError, "research_results_missing_citable_urls"):
                real_research_tool({"goal": "Research a local delivery idea", "max_queries": 1})

    def test_all_provider_failures_raise_generic_error(self):
        with patch(
            "core.src.canonical_provider_tools.search_provider",
            side_effect=RuntimeError("private provider diagnostic"),
        ):
            with self.assertRaisesRegex(RuntimeError, "research_provider_failed") as caught:
                real_research_tool({"goal": "Research a local delivery idea", "max_queries": 2})
        self.assertNotIn("private provider diagnostic", str(caught.exception))

    def test_query_count_is_always_bounded_to_six(self):
        with patch("core.src.canonical_provider_tools.search_provider") as search:
            search.return_value = {
                "results": [{"title": "Only result", "url": "https://example.net/result"}]
            }
            result = real_research_tool({"goal": "Explore a tutoring business", "max_queries": 999})
        self.assertLessEqual(result["query_count"], MAX_RESEARCH_QUERIES)
        self.assertLessEqual(search.call_count, MAX_RESEARCH_QUERIES)

    def test_invalid_payload_and_query_limit_are_rejected(self):
        with self.assertRaisesRegex(TypeError, "research_payload_must_be_mapping"):
            real_research_tool("not-a-mapping")
        with self.assertRaisesRegex(ValueError, "max_queries_invalid"):
            real_research_tool({"goal": "A useful goal", "max_queries": "many"})



class TestPatch18GovernedResearchIntegration(unittest.TestCase):
    PRINCIPAL = {
        "status": "AUTHENTICATED",
        "authenticated": True,
        "principal": "operator-01",
        "principal_id": "operator-01",
        "scopes": ["run:submit", "job:execute", "governance:evaluate"],
        "roles": ["operator"],
        "auth_method": "test",
    }

    def test_research_bootstrap_is_governed_and_executes_only_on_explicit_drive(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = RealUnifiedRuntime(directory)
            calls = []

            def fake_research(payload):
                calls.append(dict(payload))
                return {
                    "provider": "fake_search",
                    "status": "COMPLETE",
                    "query_count": 1,
                    "result_count": 1,
                    "results": [{
                        "url": "https://example.com/market",
                        "title": "Market signals",
                        "snippet": "Citable evidence",
                    }],
                }

            runtime.register_execution_tool(
                "provider.research.live", fake_research,
                version="1.0.0", retry_safe=False,
            )
            try:
                result = runtime.run(
                    run_id="PATCH18-RESEARCH-R1",
                    project_id="PATCH18-RESEARCH-P1",
                    strategy_id="PATCH18-RESEARCH-S1",
                    intent="Research a business opportunity before making a recommendation",
                    goal="Validate demand for affordable home-cooked meals",
                    audience="busy office workers",
                    constraints={"location": "Cairo", "budget": "10000 EGP"},
                    principal=self.PRINCIPAL,
                    execution_contract={
                        "action": "read_only_market_research",
                        "tool_name": "provider.research.live",
                        "payload": {
                            "goal": "Validate demand for affordable home-cooked meals",
                            "audience": "busy office workers",
                            "constraints": {"location": "Cairo", "budget": "10000 EGP"},
                            "max_queries": 1,
                        },
                    },
                )
                self.assertEqual(result["status"], "PASS")
                governed = result["governed_execution"]
                self.assertEqual(
                    governed["execution_path"], "READ_ONLY_EVIDENCE_ACQUISITION"
                )
                self.assertEqual(calls, [], "submitting a research intent must not call the tool")
                intent_id = governed["intent"]["intent_id"]
                self.assertEqual(governed["status"], "READY")

                driven = runtime.execute_governed_intent(
                    intent_id, principal=self.PRINCIPAL
                )
                self.assertEqual(driven["status"], "SUCCEEDED")
                self.assertEqual(len(calls), 1)
                self.assertEqual(
                    driven["execution"]["result"]["result_count"], 1
                )
                self.assertEqual(
                    driven["execution"]["result"]["results"][0]["url"],
                    "https://example.com/market",
                )
            finally:
                runtime.close()

    def test_bootstrap_exception_does_not_apply_to_other_tool_names(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = RealUnifiedRuntime(directory)
            calls = []
            runtime.register_execution_tool(
                "provider.search.fake",
                lambda payload: calls.append(payload) or {"ok": True},
                version="1.0.0",
            )
            try:
                result = runtime.run(
                    run_id="PATCH18-NEG-R1",
                    project_id="PATCH18-NEG-P1",
                    strategy_id="PATCH18-NEG-S1",
                    intent="Try to submit non-allowlisted research tool",
                    goal="Research demand",
                    audience="test users",
                    principal=self.PRINCIPAL,
                    execution_contract={
                        "action": "read_only_market_research",
                        "tool_name": "provider.search.fake",
                        "payload": {"query": "demand"},
                    },
                )
                governed = result.get("governed_execution") or {}
                self.assertEqual(governed.get("status"), "BLOCKED")
                self.assertNotEqual(
                    governed.get("execution_path"),
                    "READ_ONLY_EVIDENCE_ACQUISITION",
                )
                self.assertEqual(calls, [])
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
