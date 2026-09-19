import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "src" / "ui" / "ui" / "app.js"
HTML = ROOT / "src" / "ui" / "ui" / "index.html"
CSS = ROOT / "src" / "ui" / "ui" / "styles.css"

class TestO46DecisionIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = APP.read_text(encoding='utf-8')
        cls.html = HTML.read_text(encoding='utf-8')
        cls.css = CSS.read_text(encoding='utf-8')

    def test_hero_present(self):
        self.assertIn('decision-intel-hero', self.html)
        self.assertIn('decisionHeroTitle', self.html)
        self.assertIn('decisionHeroConfidence', self.html)

    def test_why_direction_surface_present(self):
        self.assertIn('decisionStory', self.html)
        self.assertIn('decisionNextBody', self.html)
        self.assertIn('WHY THIS DIRECTION', self.html)

    def test_canonical_surface_preserved(self):
        self.assertIn('CANONICAL DECISION SURFACE', self.html)
        self.assertIn('decisionSurface', self.html)

    def test_view_model_drives_hero(self):
        self.assertIn('renderDecisionIntelligenceV5(run)', self.app)
        self.assertIn('resultExtraction(run)', self.app)

    def test_explainability_fields_present(self):
        for token in ('problem', 'audience', 'promise', 'positioning', 'validationModel', 'longTermModel', 'marketScope'):
            self.assertIn(token, self.app)

    def test_next_step_is_visible(self):
        for token in ('nextAction', 'successThreshold', 'decisionRule', 'evidenceLabel'):
            self.assertIn(token, self.app)

    def test_backend_derived_language(self):
        self.assertIn('BACKEND RESULT', self.app)
        self.assertNotIn('mock decision intelligence', self.app.lower())

    def test_no_execute_controls_added(self):
        self.assertNotIn('decisionHeroApprove', self.html)
        self.assertNotIn('decisionHeroExecute', self.html)

    def test_responsive_styles_present(self):
        self.assertIn('@media(max-width:960px)', self.css)
        self.assertIn('@media(max-width:680px)', self.css)

    def test_rtl_styles_present(self):
        self.assertIn('.rtl-mode .decision-intel-hero', self.css)
        self.assertIn('.rtl-mode .decision-score-ring', self.css)

if __name__ == '__main__':
    unittest.main()
