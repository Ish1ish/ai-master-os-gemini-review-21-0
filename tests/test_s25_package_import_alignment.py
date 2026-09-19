import unittest


class TestS25PackageImportAlignment(unittest.TestCase):
    def test_strategy_namespace_and_core_package_can_coexist(self):
        from src.strategy_intelligence import StrategyIntelligence
        from src.strategy_feedback_intelligence import StrategyFeedbackIntelligence
        from src.strategy_adaptation_intelligence import StrategyAdaptationIntelligence
        from core.src.unified_decision_intelligence import UnifiedDecisionIntelligence
        from core.src.evidence_loop import ValidationEvidenceLoop

        self.assertTrue(StrategyIntelligence)
        self.assertTrue(StrategyFeedbackIntelligence)
        self.assertTrue(StrategyAdaptationIntelligence)
        self.assertTrue(UnifiedDecisionIntelligence)
        self.assertTrue(ValidationEvidenceLoop)

    def test_unified_runtime_adapters_use_canonical_core_imports(self):
        from unified_runtime.udi_adapter import build_udi_decision_adapter
        from unified_runtime.o42_adapter import O42EvidenceAdapter

        self.assertTrue(callable(build_udi_decision_adapter))
        self.assertTrue(O42EvidenceAdapter)


if __name__ == "__main__":
    unittest.main()
