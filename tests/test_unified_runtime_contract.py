import unittest

from unified_runtime.contract import STAGES, UnifiedRun, UnifiedRunError, StageStatus


class TestUnifiedRuntimeContract(unittest.TestCase):
    def test_deterministic_run_id(self):
        a = UnifiedRun.create("demo", "Validate a product idea")
        b = UnifiedRun.create("demo", "Validate a product idea")
        self.assertEqual(a.run_id, b.run_id)
        self.assertEqual(a.current_stage, "INTENT")

    def test_stages_are_ordered_and_fail_closed(self):
        run = UnifiedRun.create("demo", "x")
        with self.assertRaises(UnifiedRunError):
            run.start("DECISION")
        run.start("INTENT")
        run.finish("INTENT", {"accepted": True})
        run.start("UNDERSTAND")
        run.finish("UNDERSTAND", {})
        self.assertTrue(run.can_start("ROUTE"))
        self.assertFalse(run.can_start("EVIDENCE"))

    def test_successful_progression_preserves_trace(self):
        run = UnifiedRun.create("demo", "x")
        run.start("INTENT", "TRC-1")
        run.finish("INTENT", {"normalized": "x"})
        run.start("UNDERSTAND", "TRC-1")
        run.finish("UNDERSTAND", {"confidence": "high"})
        snap = run.snapshot()
        self.assertEqual(snap["stages"]["INTENT"]["trace_id"], "TRC-1")
        self.assertEqual(snap["stages"]["INTENT"]["status"], "SUCCEEDED")

    def test_terminal_stop_prevents_next_stage(self):
        run = UnifiedRun.create("demo", "x")
        run.start("INTENT")
        run.stop("INTENT", StageStatus.BLOCKED, "missing permission")
        self.assertTrue(run.terminal)
        with self.assertRaises(UnifiedRunError):
            run.start("UNDERSTAND")

    def test_all_stages_are_canonical(self):
        self.assertEqual(STAGES[-1], "NEXT_DECISION")
        self.assertEqual(len(STAGES), 13)


if __name__ == "__main__":
    unittest.main()
