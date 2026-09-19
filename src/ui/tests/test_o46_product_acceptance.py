import re
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
APP=(ROOT/"src/ui/ui/app.js").read_text(encoding="utf-8")
HTML=(ROOT/"src/ui/ui/index.html").read_text(encoding="utf-8")
CSS=(ROOT/"src/ui/ui/styles.css").read_text(encoding="utf-8")

class TestO46ProductAcceptance(unittest.TestCase):
    def test_page_present(self): self.assertIn('id="page-acceptance"', HTML)
    def test_navigation_present(self): self.assertIn('data-page="acceptance"', HTML)
    def test_live_run_selector_present(self): self.assertIn('id="acceptanceRunSelect"', HTML)
    def test_backend_get_only(self):
        block=APP[APP.find('async function runProductAcceptance'):APP.find('async function runProductAcceptance')+7000]
        self.assertIn("api('/runs?limit=20')", block); self.assertNotIn("method:'POST'", block); self.assertNotIn("method:'PUT'", block); self.assertNotIn("method:'DELETE'", block)
    def test_acceptance_checks_nine_surface_items(self):
        self.assertGreaterEqual(len(re.findall(r"checks\.push\(\[", APP)), 9)
    def test_no_execution_endpoint(self): self.assertNotIn('/execute', APP[APP.find('async function runProductAcceptance'):APP.find('async function runProductAcceptance')+7000])
    def test_no_approval_mutation(self): self.assertNotIn("method:'POST'", APP[APP.find('async function runProductAcceptance'):APP.find('async function runProductAcceptance')+7000])
    def test_experience_boundary_copy_present(self): self.assertIn('Presentation is not authority.', APP)
    def test_responsive_styles_present(self): self.assertIn('.acceptance-grid{grid-template-columns:1fr}', CSS)

if __name__=='__main__': unittest.main()
