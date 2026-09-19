from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'ui'

class TestV506TypographyIconPolish(unittest.TestCase):
    def test_font_stack_and_antialiasing_present(self):
        css = (UI / 'styles.css').read_text(encoding='utf-8')
        self.assertIn('--font-ui:', css)
        self.assertIn('-webkit-font-smoothing:antialiased', css)
        self.assertIn('text-rendering:optimizeLegibility', css)

    def test_navigation_icons_are_larger_and_clearer(self):
        css = (UI / 'styles.css').read_text(encoding='utf-8')
        self.assertIn('font-size:18px!important', css)
        self.assertIn('width:28px!important', css)
        self.assertIn('height:28px!important', css)
        self.assertIn('border-radius:9px!important', css)

    def test_toolbar_icons_and_controls_are_larger(self):
        css = (UI / 'styles.css').read_text(encoding='utf-8')
        self.assertIn('width:40px!important;height:40px!important', css)
        self.assertIn('notification-glyph{width:20px!important;height:20px!important', css)

    def test_typography_scale_is_upgraded(self):
        css = (UI / 'styles.css').read_text(encoding='utf-8')
        self.assertIn('.page h2{font-size:30px', css)
        self.assertIn('.page h3{font-size:17px', css)
        self.assertIn('.nav-item b{font-size:13.25px!important', css)

    def test_meta_records_visual_polish(self):
        meta = json.loads((UI / 'meta.json').read_text(encoding='utf-8'))
        self.assertEqual(meta.get('integrated_version'), '5.0.6')
        self.assertEqual(meta.get('typography_icon_polish'), '5.0.6')

if __name__ == '__main__':
    unittest.main()
