import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
APP=ROOT/'src/ui/ui/app.js'
HTML=ROOT/'src/ui/ui/index.html'
CSS=ROOT/'src/ui/ui/styles.css'

class TestGoldenRunControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=APP.read_text(encoding='utf-8')
        cls.html=HTML.read_text(encoding='utf-8')
        cls.css=CSS.read_text(encoding='utf-8')
    def test_page_present(self): self.assertIn('page-goldenrun',self.html)
    def test_navigation_present(self): self.assertIn('data-page="goldenrun"',self.html)
    def test_create_uses_runs_post(self): self.assertIn("api('/runs',{method:'POST'",self.app)
    def test_execute_requires_explicit_click(self): self.assertIn("id=\"goldenExecuteBtn\"",self.html); self.assertIn("addEventListener('click',async()=>",self.app)
    def test_execute_endpoint_is_governed(self): self.assertIn("/execute`, {method:'POST'",self.app)
    def test_no_auto_execute_on_init(self): self.assertIn('Run created. Execution is still waiting for your explicit action.',self.app)
    def test_live_reload_uses_backend_get(self): self.assertIn("api(`/runs/${encodeURIComponent(jobId)}`)",self.app)
    def test_learning_and_approval_are_descriptive(self):
        self.assertIn("/learning/context?project_id=",self.app)
        self.assertIn("api('/approvals')",self.app)
    def test_safety_boundary_copy(self): self.assertIn('Human approval remains authoritative',self.app); self.assertIn('user-initiated',self.html.lower())
    def test_responsive_surface(self): self.assertIn('@media(max-width:980px)',self.css); self.assertIn('@media(max-width:560px)',self.css)
    def test_readable_journey(self):
        for key in ('goldenControlRunStatus','goldenControlGovernance','goldenControlNext','goldenControlSteps'):
            self.assertIn(key,self.html)
    def test_compile_surface_markers(self): self.assertIn('UI13-O46 Golden Run Control',self.app); self.assertIn('UI13-O46 Golden Run Control',self.css)

if __name__=='__main__': unittest.main()
