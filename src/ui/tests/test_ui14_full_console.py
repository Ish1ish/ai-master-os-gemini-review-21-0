
import pathlib, re, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
UI=ROOT/'ui'
class TestUI14FullConsole(unittest.TestCase):
    def setUp(self):
        self.index=(UI/'index.html').read_text(encoding='utf-8')
        self.js=(UI/'ux14_console.js').read_text(encoding='utf-8')
        self.css=(UI/'ux14_console.css').read_text(encoding='utf-8')
    def test_all_navigation_pages_are_designed(self):
        pages=re.findall(r'data-page="([^"]+)"',self.index)
        for p in pages:
            self.assertIn("mount('"+p+"'",self.js, msg=p)
    def test_full_console_flag(self): self.assertIn('window.UI14_FULL_CONSOLE=true',self.js)
    def test_semantic_field_labels_are_present(self):
        for token in ('Goal','Target customer','Scope','Constraints','Evidence boundary','Decision rule','Next action'):
            self.assertIn(token,self.js)
    def test_no_new_external_autonomy(self):
        self.assertNotIn('window.open(',self.js)
        self.assertNotIn('sendMail',self.js)
        self.assertIn("'/runs'",self.js)
    def test_responsive_tokens(self):
        self.assertIn('@media (max-width:860px)',self.css)
        self.assertIn('@media (max-width:560px)',self.css)
    def test_governance_boundary_visible(self):
        for token in ('Human approval','backend-controlled','No automatic continuation'):
            self.assertIn(token,self.js)
    def test_overlay_hooks_exist(self):
        self.assertIn('ux14_console.css?v=1.0.0',self.index)
        self.assertIn('ux14_console.js?v=1.0.0',self.index)
if __name__=='__main__': unittest.main()
