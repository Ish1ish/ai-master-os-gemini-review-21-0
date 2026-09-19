import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'ui' / 'index.html'
APP = ROOT / 'ui' / 'app.js'
CSS = ROOT / 'ui' / 'styles.css'

class TestO46GoldenLiveInspector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = INDEX.read_text(encoding='utf-8')
        cls.app = APP.read_text(encoding='utf-8')
        cls.css = CSS.read_text(encoding='utf-8')

    def test_inspector_present(self):
        self.assertIn('goldenLiveInspector', self.index)
        self.assertIn('goldenValidationGrid', self.index)

    def test_run_selector_present(self):
        self.assertIn('goldenRunSelect', self.index)
        self.assertIn('goldenInspectRefresh', self.index)

    def test_get_only_inspection_paths(self):
        self.assertIn("api('/runs?limit=20')", self.app)
        self.assertIn("api(`/runs/${encodeURIComponent(chosen.job_id||chosen.id)}`)", self.app)
        self.assertNotIn("/runs/\${encodeURIComponent(chosen.job_id||chosen.id)}/execute", self.app)

    def test_learning_is_loaded(self):
        self.assertIn('/learning/context?project_id=', self.app)

    def test_approval_is_descriptive(self):
        self.assertIn("api('/approvals')", self.app)
        self.assertIn('Approval is descriptive only in this inspector.', self.app)

    def test_backend_derived(self):
        self.assertIn('buildGoldenInspectorReport', self.app)
        self.assertIn('buildO46ExperienceView', self.app)

    def test_coherence_checks(self):
        for label in ['Intent visible','Research visible','Decision explainable','Governance visible','Approval coherent','Outcome visible','Learning visible','Next decision visible']:
            self.assertIn(label, self.app)

    def test_read_only_marker(self):
        self.assertIn('GET-only inspector', self.app)
        self.assertIn('No POST/PUT/DELETE is issued by UI11.', self.app)

    def test_responsive_css_contract(self):
        self.assertIn('golden-live-inspector', self.css)
        self.assertIn('golden-check-card', self.css)

    def test_no_silent_fake_values(self):
        self.assertIn('No invented recommendation is allowed.', self.app)

    def test_stage_view_updates(self):
        self.assertIn('window.__O46_EXPERIENCE_VIEW__=view', self.app)
        self.assertIn('renderO46GoldenExperience(view)', self.app)

    def test_compile_surface(self):
        self.assertIn('function inspectGoldenRun', self.app)

if __name__ == '__main__':
    unittest.main()
