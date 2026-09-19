import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HTML=(ROOT/"src/ui/ui/index.html").read_text(encoding="utf-8")
APP=(ROOT/"src/ui/ui/app.js").read_text(encoding="utf-8")
CSS=(ROOT/"src/ui/ui/styles.css").read_text(encoding="utf-8")

class TestO46OutcomeLearning(unittest.TestCase):
    def test_outcome_learning_center_present(self):
        for token in ("outcome-learning-hero","OUTCOME · LEARNING · ADAPTATION","olOutcomeStatus","olNextDecision"):
            self.assertIn(token, HTML)
    def test_observed_outcome_surface(self):
        for token in ("olOutcomeTitle","olOutcomeSummary","olOutcomeFacts","OBSERVED OUTCOME"):
            self.assertIn(token, HTML)
    def test_learning_surface(self):
        for token in ("olLearningSignals","LEARNING SIGNAL","olLearningTimeline"):
            self.assertIn(token, HTML)
    def test_adaptation_surface(self):
        for token in ("olPreviousStrategy","olCurrentStrategy","olAdaptationState","STRATEGY ADAPTATION"):
            self.assertIn(token, HTML)
    def test_next_decision_surface(self):
        for token in ("olNextDecision","olNextDecisionReason","NEXT DECISION"):
            self.assertIn(token, HTML)
    def test_backend_learning_endpoint_preserved(self):
        self.assertIn("/learning/context?project_id=", APP)
    def test_backend_derived_no_fabricated_learning(self):
        self.assertIn("fetchLearningContextV42", APP)
        self.assertIn("No learning records exposed", APP)
    def test_read_only(self):
        self.assertNotIn("olApprove", APP)
        self.assertNotIn("olExecute", APP)
    def test_explainability(self):
        for token in ("olExplainBtn","Why the next decision changed","olExplainGrid"):
            self.assertIn(token, APP+HTML)
    def test_responsive(self):
        self.assertIn("@media(max-width:900px)", CSS)
        self.assertIn("@media(max-width:640px)", CSS)
    def test_rtl(self):
        self.assertIn(".rtl-mode .outcome-learning-status", CSS)
        self.assertIn(".rtl-mode .learning-timeline-item", CSS)

if __name__ == "__main__":
    unittest.main()
