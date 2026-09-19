import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HTML = (ROOT / 'src/ui/ui/index.html').read_text(encoding='utf-8')
APP = (ROOT / 'src/ui/ui/app.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src/ui/ui/styles.css').read_text(encoding='utf-8')

class TestO46Explainability(unittest.TestCase):
    def test_global_explainability_layer_present(self):
        for token in ('o46ExplainDrawer','o46ExplainOverlay','o46ExplainTitle','o46ExplainClose'):
            self.assertIn(token, HTML)

    def test_explainability_actions_cover_core_surfaces(self):
        for token in ('data-explain-section="decision"','data-explain-section="evidence"','data-explain-section="governance"','data-explain-section="outcome"'):
            self.assertIn(token, HTML)

    def test_explainability_builder_is_present(self):
        for token in ('buildO46Explainability','WHY THIS RESULT','EVIDENCE USED','GOVERNANCE CONTEXT','WHAT HAPPENS NEXT'):
            self.assertIn(token, APP)

    def test_backend_derived_only(self):
        for token in ('window.__O46_EXPERIENCE_VIEW__','No backend-derived context is available'):
            self.assertIn(token, APP)

    def test_no_execution_controls_added(self):
        self.assertNotIn('o46ExplainApprove', APP+HTML)
        self.assertNotIn('o46ExplainExecute', APP+HTML)

    def test_escape_and_safe_rendering(self):
        self.assertIn('esc(value)', APP)
        self.assertIn('escapeHtml', APP)

    def test_explainability_sections(self):
        for token in ('explain-card','explain-source','explain-reason','explain-impact'):
            self.assertIn(token, CSS)

    def test_overlay_responsive(self):
        self.assertIn('@media(max-width:900px)', CSS)
        self.assertIn('@media(max-width:640px)', CSS)

    def test_rtl_support(self):
        for token in ('.rtl-mode .o46-explain-drawer','.rtl-mode .explain-card','.rtl-mode .o46-explain-grid-v2'):
            self.assertIn(token, CSS)

    def test_stage_specific_explanations(self):
        for token in ('intent','research','decision','governance','approval','execution','outcome','learning','next_step'):
            self.assertIn(f"case '{token}'", APP)

if __name__ == '__main__':
    unittest.main()
