import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / 'ui'
INDEX = UI / 'ui' / 'index.html'
SCRIPT = UI / 'ui' / 'o46_golden_control_fix.js'

class TestO46GoldenControlExperienceFix(unittest.TestCase):
    def test_fix_script_exists(self):
        self.assertTrue(SCRIPT.is_file())

    def test_index_loads_fix(self):
        html = INDEX.read_text(encoding='utf-8')
        self.assertIn('o46_golden_control_fix.js?v=1.0.0', html)

    def test_golden_controls_are_wired(self):
        js = SCRIPT.read_text(encoding='utf-8')
        for marker in [
            'goldenCreateBtn', 'goldenExecuteBtn', 'goldenInspectBtn',
            'goldenOpenExperience', 'goldenRefresh', 'goldenRunSelect',
            "api('/runs'", "/runs/' + encodeURIComponent(id) + '/execute"
        ]:
            self.assertIn(marker, js)

    def test_no_automatic_execution_on_boot(self):
        js = SCRIPT.read_text(encoding='utf-8')
        boot = js[js.index('async function boot()'):js.index("if (document.readyState")]
        self.assertNotIn("'/execute'", boot)

    def test_no_secret_rendering(self):
        js = SCRIPT.read_text(encoding='utf-8')
        self.assertNotIn('sessionStorage.getItem(\'aios.bearer\')', js)

if __name__ == '__main__':
    unittest.main()
