import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / 'ui' / 'ui'
JS = UI / 'ux15_console.js'
CSS = UI / 'ux15_console.css'
HTML = UI / 'index.html'

PAGES = ['overview','runs','golden','acceptance','goldenrun','decisions','evidence','experiments','memory','adaptation','approvals','policies','execution','recovery','audit','health','operations','release','settings','platform','guide']

class TestUI15FullConsoleWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = JS.read_text(encoding='utf-8')
        cls.css = CSS.read_text(encoding='utf-8')
        cls.html = HTML.read_text(encoding='utf-8')

    def test_all_navigation_pages_have_renderers(self):
        for p in PAGES:
            self.assertRegex(self.js, rf'\b{p}:render[A-Z][A-Za-z]+')
            self.assertIn(f'id="page-{p}"', self.html)

    def test_live_read_wiring_is_present(self):
        for endpoint in ['/runs?limit=25', '/learning/context?project_id=', '/approvals', '/experiments', '/health', '/ready']:
            self.assertIn(endpoint, self.js)

    def test_explicit_run_mutations_only(self):
        self.assertIn("api('/runs',{method:'POST'", self.js)
        self.assertIn("'/execute',{method:'POST'", self.js)
        self.assertNotIn("/approvals',{method:'POST'", self.js)
        self.assertNotIn("/memory',{method:'POST'", self.js)

    def test_semantic_mapping_fields_are_distinct(self):
        for field in ['request','goal','audience','scope','constraints']:
            self.assertIn(field, self.js)
        self.assertIn("target_customer", self.js)
        self.assertIn("long_term_product_model", self.js)
        self.assertIn("validation_model", self.js)

    def test_loading_error_empty_states_are_present(self):
        for token in ['Backend state unavailable','No source items are exposed.','No experiments exposed yet.','No approval records exposed.','No event array is exposed']:
            self.assertIn(token, self.js)

    def test_backend_authority_copy_is_preserved(self):
        for token in ['Presentation is not policy authority','Consequential external actions remain human-governed','Approval never equals execution']:
            self.assertIn(token, self.js)

    def test_responsive_tokens_exist(self):
        self.assertIn('@media (max-width:900px)', self.css)
        self.assertIn('@media (max-width:560px)', self.css)

    def test_canonical_ui_assets_are_loaded(self):
        self.assertIn('ux14_console.css?v=1.0.0', self.html)
        self.assertIn('ux14_console.js?v=1.0.0', self.html)
        self.assertIn('ux16_experience.js?v=1.0.0', self.html)
        self.assertNotIn('ux15_console.css?v=1.0.0', self.html)
        self.assertNotIn('ux15_console.js?v=1.0.0', self.html)

    def test_no_secret_rendering(self):
        self.assertNotIn("console.log(sessionStorage.getItem('aios.bearer'))", self.js)
        self.assertNotIn('token.slice', self.js)

if __name__ == '__main__':
    unittest.main()
