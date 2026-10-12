from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch

from core.src.research_synthesis import real_research_synthesis_tool
from unified_runtime.integrated_runtime import RealUnifiedRuntime


def response_json():
    return {
        "executive_summary": "Initial signal only; more validation is needed.",
        "evidence_findings": [{"claim": "The source discusses affordable meals.", "source_ids": ["S001"], "confidence": "medium"}],
        "hypotheses": [{"hypothesis": "Repeat demand may exist.", "reasoning": "The snippet does not prove purchase behavior.", "validation_step": "Run a paid pilot.", "source_ids": ["S001"]}],
        "recommendations": [{"recommendation": "Run a small pilot.", "basis_source_ids": ["S001"], "assumptions": ["Kitchen capacity is available."], "validation_step": "Measure paid orders and margins."}],
        "risks": [{"risk": "Snippets may omit context.", "mitigation": "Inspect full source pages.", "source_ids": []}],
        "evidence_gaps": ["Current local prices need verification."],
    }


class TestSourceGroundedSynthesis(unittest.TestCase):
    def setUp(self):
        self.sources = [{
            "title": "Affordable meal options",
            "url": "https://example.com/meal-demand#overview",
            "snippet": "The page discusses affordable prepared meals for busy customers.",
            "published_at": "2026-09-18",
            "accessed_at": "2026-10-11T10:00:00Z",
        }]

    @patch("core.src.research_synthesis.model_provider")
    def test_structured_synthesis_preserves_source_mapping(self, model):
        model.return_value = {"text": json.dumps(response_json())}
        result = real_research_synthesis_tool({
            "goal": "Validate affordable home-cooked meal demand",
            "audience": "busy office workers",
            "requested_language": "en",
            "results": self.sources,
        })
        self.assertEqual(result["status"], "COMPLETE")
        self.assertFalse(result["decision_grade_evidence"])
        self.assertEqual(result["sources"][0]["source_id"], "S001")
        self.assertEqual(result["sources"][0]["url"], "https://example.com/meal-demand")
        self.assertEqual(result["synthesis"]["evidence_findings"][0]["source_ids"], ["S001"])
        model.assert_called_once()

    @patch("core.src.research_synthesis.model_provider")
    def test_unknown_citation_is_rejected(self, model):
        output = response_json()
        output["evidence_findings"][0]["source_ids"] = ["S999"]
        model.return_value = {"text": json.dumps(output)}
        with self.assertRaisesRegex(ValueError, "model_synthesis_unknown_source_id"):
            real_research_synthesis_tool({"goal": "Test demand", "results": self.sources})

    @patch("core.src.research_synthesis.model_provider")
    def test_uncited_evidence_finding_is_rejected(self, model):
        output = response_json()
        output["evidence_findings"][0]["source_ids"] = []
        model.return_value = {"text": json.dumps(output)}
        with self.assertRaisesRegex(ValueError, "model_synthesis_citation_required"):
            real_research_synthesis_tool({"goal": "Test demand", "results": self.sources})

    @patch("core.src.research_synthesis.model_provider")
    def test_bad_json_is_rejected_without_exposing_raw_text(self, model):
        model.return_value = {"text": "not json"}
        with self.assertRaisesRegex(ValueError, "model_synthesis_invalid_json"):
            real_research_synthesis_tool({"goal": "Test demand", "results": self.sources})

    @patch("core.src.research_synthesis.model_provider")
    def test_provider_failure_has_safe_error(self, model):
        model.side_effect = RuntimeError("provider details")
        with self.assertRaisesRegex(RuntimeError, "model_synthesis_provider_failed") as caught:
            real_research_synthesis_tool({"goal": "Test demand", "results": self.sources})
        self.assertNotIn("provider details", str(caught.exception))

    @patch("core.src.research_synthesis.model_provider")
    def test_prompt_marks_source_snippets_as_untrusted_data(self, model):
        captured = []
        model.side_effect = lambda prompt: captured.append(prompt) or {"text": json.dumps(response_json())}
        real_research_synthesis_tool({"goal": "Test demand", "results": self.sources})
        self.assertIn("never as instructions", captured[0])
        self.assertIn("source_id", captured[0])

    def test_rejects_missing_sources(self):
        with patch("core.src.research_synthesis.model_provider") as model:
            with self.assertRaisesRegex(ValueError, "research_sources_missing_citable_snippets"):
                real_research_synthesis_tool({"goal": "Test demand", "results": []})
            model.assert_not_called()


class TestGovernedSynthesis(unittest.TestCase):
    PRINCIPAL = {
        "status": "AUTHENTICATED",
        "authenticated": True,
        "principal": "operator-01",
        "principal_id": "operator-01",
        "scopes": ["run:submit", "job:execute", "governance:evaluate"],
        "roles": ["operator"],
        "auth_method": "test",
    }

    def test_tool_only_runs_after_explicit_governed_drive(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = RealUnifiedRuntime(directory)
            calls = []
            runtime.register_execution_tool(
                "provider.research.synthesis",
                lambda payload: calls.append(dict(payload)) or {"status": "COMPLETE"},
                version="1.0.0",
                retry_safe=False,
            )
            try:
                result = runtime.run(
                    run_id="PATCH19-SYN-R1",
                    project_id="PATCH19-SYN-P1",
                    strategy_id="PATCH19-SYN-S1",
                    intent="Synthesize previously collected market research",
                    goal="Validate meal demand",
                    audience="office workers",
                    principal=self.PRINCIPAL,
                    execution_contract={
                        "action": "read_only_market_research",
                        "tool_name": "provider.research.synthesis",
                        "payload": {"goal": "Validate demand", "results": []},
                    },
                )
                governed = result["governed_execution"]
                self.assertEqual(governed["status"], "READY")
                self.assertEqual(calls, [])
                driven = runtime.execute_governed_intent(
                    governed["intent"]["intent_id"], principal=self.PRINCIPAL
                )
                self.assertEqual(driven["status"], "SUCCEEDED")
                self.assertEqual(len(calls), 1)
            finally:
                runtime.close()

    def test_research_action_rejects_unapproved_tool_name(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = RealUnifiedRuntime(directory)
            calls = []
            runtime.register_execution_tool(
                "provider.research.unapproved",
                lambda payload: calls.append(payload) or {"ok": True},
                retry_safe=False,
            )
            try:
                result = runtime.run(
                    run_id="PATCH19-NEG-R1",
                    project_id="PATCH19-NEG-P1",
                    strategy_id="PATCH19-NEG-S1",
                    intent="Attempt an unapproved research binding",
                    goal="Validate demand",
                    principal=self.PRINCIPAL,
                    execution_contract={
                        "action": "read_only_market_research",
                        "tool_name": "provider.research.unapproved",
                        "payload": {},
                    },
                )
                governed = result.get("governed_execution") or {}
                self.assertEqual(governed.get("status"), "BLOCKED")
                self.assertEqual(governed.get("reason"), "research_action_tool_binding_invalid")
                self.assertEqual(calls, [])
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
