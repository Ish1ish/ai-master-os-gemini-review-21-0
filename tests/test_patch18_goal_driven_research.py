from __future__ import annotations

import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
