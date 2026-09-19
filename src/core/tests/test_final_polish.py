import unittest

from engines.o8.src.metrics import MetricsCollector
from src.real_wiring import O23Runtime
from src.providers import fake_model_provider, fake_search_provider


class TestFinalPolish(unittest.TestCase):
    def test_metrics_expose_canonical_qa_status(self):
        events = [
            {"run_id":"R1","event_type":"run_start","status":"STARTED","timestamp":"2026-09-11T08:00:00+00:00"},
            {"run_id":"R1","event_type":"qa","status":"PASS","timestamp":"2026-09-11T08:00:01+00:00"},
            {"run_id":"R1","event_type":"run_end","status":"COMPLETE","timestamp":"2026-09-11T08:00:02+00:00"},
        ]
        out = MetricsCollector().summarize_run("R1", events)
        self.assertEqual(out["qa_status"], "PASS")
        self.assertEqual(out["qa_pass_count"], 1)
        self.assertEqual(out["qa_fail_or_refine_count"], 0)

    def test_runtime_result_exposes_top_level_qa_summary(self):
        runtime = O23Runtime(model_provider=fake_model_provider, search_provider=fake_search_provider)
        try:
            out = runtime.run(
                "JOB-FINAL-POLISH-001", "PROJ-TEST",
                "Research AI automation for small businesses.",
                audience="small businesses",
                goal="validate a lean business opportunity",
                constraints=["low startup cost", "simple MVP"],
            )
            self.assertEqual(out["status"], "COMPLETE")
            self.assertEqual(out["qa"]["status"], "PASS")
            self.assertEqual(out["qa"]["checks"]["handoff_chain"], "PASS")
            self.assertEqual(out["qa"]["handoff_count"], 13)
            self.assertEqual(out["handoff_chain_qa"]["status"], "PASS")
        finally:
            runtime.close()


if __name__ == "__main__":
    unittest.main()
