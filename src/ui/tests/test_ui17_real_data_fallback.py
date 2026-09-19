import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JS = ROOT / 'ui' / 'ui' / 'ux16_experience.js'

class TestUI17RealDataFallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = JS.read_text(encoding='utf-8')

    def test_preferred_run_is_rehydrated_first(self):
        self.assertIn("sessionStorage.getItem('aios.lastJobId')", self.js)
        self.assertIn("api('/runs/' + encodeURIComponent(preferred))", self.js)

    def test_safe_run_list_limit(self):
        self.assertIn("api('/runs?limit=25')", self.js)
        self.assertNotIn("api('/runs?limit=100')", self.js)

    def test_backend_authority_preserved(self):
        self.assertIn("Backend ready · data unavailable", self.js)
        self.assertNotIn("api('/approvals',{method:'POST'", self.js)
        self.assertNotIn("api('/memory',{method:'POST'", self.js)

if __name__ == '__main__':
    unittest.main()
