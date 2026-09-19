from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
UI=ROOT/"ui"

class TestO46RunStory(unittest.TestCase):
    def setUp(self):
        self.html=(UI/"index.html").read_text(encoding="utf-8")
        self.app=(UI/"app.js").read_text(encoding="utf-8")
        self.css=(UI/"styles.css").read_text(encoding="utf-8")
        self.exp=(UI/"experience.js").read_text(encoding="utf-8")
    def test_run_story_shell(self):
        self.assertIn('id="o46RunStory"',self.html)
        self.assertIn('renderO46RunStory',self.app)
    def test_all_journey_stages_present(self):
        for token in ["intent","research","decision","governance","approval","execution","outcome","learning","next_step"]:
            self.assertIn(f"['{token}'",self.exp)
    def test_stage_details_are_backend_derived(self):
        for token in ["view.research.summary","view.decision.recommendation","view.governance.decision","view.approval.required","view.execution.status","view.outcome.status","view.learning.signal","view.next_step.recommendation"]:
            self.assertIn(token,self.exp)
    def test_story_is_interactive(self):
        for token in ["data-story-stage","addEventListener('click'","runStoryDetail"]:
            self.assertIn(token,self.exp)
    def test_visual_system_present(self):
        for token in [".run-story-card",".run-story-track",".run-story-node",".run-story-detail"]:
            self.assertIn(token,self.css)
    def test_build_version(self):
        self.assertIn("O46_EXPERIENCE_RUN_STORY_BUILD = '1.2.0'",self.exp)

if __name__=='__main__': unittest.main()
