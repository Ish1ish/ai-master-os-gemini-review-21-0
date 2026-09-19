import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui"

class TestO46VisualPolish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (UI / "index.html").read_text(encoding="utf-8")
        cls.css = (UI / "styles.css").read_text(encoding="utf-8")
        cls.js = (UI / "app.js").read_text(encoding="utf-8")

    def test_version_marker(self):
        self.assertIn("UI9 · Visual Experience Polish v5.1.0", self.html)
        self.assertIn('styles.css?v=5.1.0', self.html)

    def test_design_tokens_present(self):
        for token in ("--ui9-radius-xl", "--ui9-shadow", "--ui9-glow", "--ui9-line"):
            self.assertIn(token, self.css)

    def test_interaction_polish_present(self):
        for token in (".card:hover", ":focus-visible", ".primary-btn:hover", ".o46-motion-ready"):
            self.assertIn(token, self.css)

    def test_motion_system_present(self):
        for token in (".o46-motion-ready", "@keyframes ui9-rise", ".ui9-loading-shimmer", "prefers-reduced-motion"):
            self.assertIn(token, self.css)
        self.assertIn("o46-motion-ready", self.js)
        self.assertIn("reduced-motion", self.js)

    def test_accessibility_focus_present(self):
        self.assertIn("focus-visible", self.css)
        self.assertIn("reduced-motion", self.js)

    def test_responsive_polish_present(self):
        self.assertIn("@media(max-width:900px)", self.css)
        self.assertIn("@media(max-width:700px)", self.css)

    def test_no_new_execution_controls(self):
        for needle in ("execute", "publish", "send external"):
            self.assertNotIn(f'UI9-{needle}', self.html + self.css + self.js)

    def test_ui9_metadata(self):
        self.assertIn("ui9", self.js.lower())
        self.assertIn("visual-polish-5.1", self.js)

if __name__ == "__main__":
    unittest.main()
