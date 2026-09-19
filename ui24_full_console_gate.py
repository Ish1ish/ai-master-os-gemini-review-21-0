from pathlib import Path
import re, unittest
ROOT=Path(__file__).resolve().parent
UI=ROOT/'src'/'ui'/'ui'
INDEX=UI/'index.html'
JS=UI/'ui24_console.js'
CSS=UI/'ui24_console.css'
class TestUI24FullConsole(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=INDEX.read_text(encoding='utf-8'); cls.js=JS.read_text(encoding='utf-8'); cls.css=CSS.read_text(encoding='utf-8')
    def test_assets_present(self): self.assertTrue(JS.exists()); self.assertTrue(CSS.exists()); self.assertIn('ui24_console.js?v=24.0.0',self.html)
    def test_legacy_overlays_removed(self):
        for token in ['ui19_console.js','ui20_console.js','ui21_console.js','ui22_console.js']:
            self.assertNotIn(token,self.html)
    def test_all_navigation_pages_exist(self):
        pages=re.findall(r'data-page="([^"]+)"',self.html); self.assertGreaterEqual(len(set(pages)),21)
    def test_recovery_playbook_not_stray(self):
        outside=self.html.split('id="page-recovery"',1)[1].split('id="page-health"',1)[0]
        self.assertEqual(outside.count('RECONCILIATION PLAYBOOK'),1)
    def test_canonical_run_contract(self):
        self.assertIn("/runs?limit=25",self.js); self.assertIn("/runs/'+encodeURIComponent(id)",self.js)
    def test_learning_is_human_readable(self):
        self.assertIn('summaryValue',self.js); self.assertNotIn('JSON.stringify(v.learning',self.js)
    def test_no_destructive_api_from_ui24(self):
        self.assertNotRegex(self.js,r'\b(?:POST|PUT|PATCH|DELETE)\b')
    def test_governance_boundary_preserved(self):
        self.assertIn('approval is backend-controlled',self.js.lower()); self.assertIn('human-gated',self.js.lower())
    def test_single_page_enforcement(self):
        self.assertIn("document.querySelectorAll('.page').forEach",self.js); self.assertIn("p.classList.add('hidden')",self.js)
    def test_major_surface_markers(self):
        for marker in ['page-overview','page-golden','page-acceptance','page-goldenrun','page-experiments','page-memory','page-adaptation','page-evidence','page-decisions','page-approvals','page-policies','page-audit','page-guide']:
            self.assertIn(marker,self.html)
if __name__=='__main__':
    unittest.main(verbosity=2)
    print('UI24_O46_FULL_CONSOLE_EXPERIENCE_PASS')
