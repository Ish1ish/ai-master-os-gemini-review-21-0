import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INDEX = ROOT / "src" / "ui" / "ui" / "index.html"
APP = ROOT / "src" / "ui" / "ui" / "app.js"
CSS = ROOT / "src" / "ui" / "ui" / "styles.css"

class TestO46GoldenExperience(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = INDEX.read_text(encoding="utf-8")
        cls.app = APP.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")

    def test_golden_page_present(self): self.assertIn('id="page-golden"', self.index)
    def test_golden_navigation_present(self): self.assertIn('data-page="golden"', self.index)
    def test_nine_stage_journey_present(self):
        for label in ("Intent","Research","Decision","Governance","Approval","Execution","Outcome","Learning","Next Decision"):
            self.assertIn(label, self.app)
    def test_backend_experience_view_used(self):
        self.assertIn('window.__O46_EXPERIENCE_VIEW__', self.app)
        self.assertIn('buildO46ExperienceView(null)', self.app)
    def test_golden_refresh_uses_existing_experience_refresh(self):
        self.assertIn('refreshO46Experience()', self.app)
    def test_read_only_marker(self): self.assertIn('READ-ONLY EXPERIENCE QA', self.index)
    def test_no_new_execute_action_in_golden_renderer(self):
        start=self.app.find('/* UI10-O46: Full Product Golden Experience')
        self.assertNotEqual(start,-1)
        block=self.app[start:]
        self.assertNotIn('run-execute', block)
        self.assertNotIn('publish', block.lower())
    def test_golden_next_surface_present(self):
        for token in ('goldenNext','goldenDecision','goldenGovernance','goldenOutcome'):
            self.assertIn(token, self.index)
    def test_visual_responsive_layer_present(self):
        self.assertIn('.golden-journey', self.css)
        self.assertIn('@media(max-width:760px)', self.css)
    def test_reduced_motion_present(self): self.assertIn('prefers-reduced-motion:reduce', self.css)
    def test_explainability_hook_present(self): self.assertIn('openExplainabilityDrawer', self.app)
    def test_backend_derived_language_present(self): self.assertIn('Backend-derived', self.app)
    def test_no_memory_mutation_from_golden_layer(self):
        start=self.app.find('/* UI10-O46: Full Product Golden Experience')
        block=self.app[start:]
        self.assertNotIn('memory.save', block)
        self.assertNotIn('writeMemory', block)
    def test_no_external_action_from_golden_layer(self):
        start=self.app.find('/* UI10-O46: Full Product Golden Experience')
        block=self.app[start:]
        self.assertNotIn('external_action', block)
    def test_page_title_hook_present(self): self.assertIn("golden:'Golden Experience'", self.app)
    def test_page_refresh_hook_present(self): self.assertIn("pageName === 'golden'", self.app)

if __name__ == '__main__': unittest.main()
