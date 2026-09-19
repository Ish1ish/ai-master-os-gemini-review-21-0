from pathlib import Path
import re, unittest
ROOT=Path(__file__).resolve().parent; UI=ROOT/'src'/'ui'/'ui'; INDEX=UI/'index.html'; JS=UI/'ui25_console.js'; CSS=UI/'ui25_console.css'
class TestUI25(unittest.TestCase):
  @classmethod
  def setUpClass(cls): cls.html=INDEX.read_text(encoding='utf-8'); cls.js=JS.read_text(encoding='utf-8'); cls.css=CSS.read_text(encoding='utf-8')
  def test_assets(self): self.assertTrue(JS.exists()); self.assertTrue(CSS.exists()); self.assertIn('ui25_console.js?v=25.0.0',self.html)
  def test_structured_parser(self): self.assertIn('JSON.parse',self.js); self.assertIn('observed_bottleneck',self.js)
  def test_learning_cleanup(self): self.assertIn('u24-learning-copy',self.js); self.assertIn('u24-step:nth-child(8)',self.js)
  def test_no_mutation_methods(self): self.assertNotRegex(self.js,r'\b(?:POST|PUT|PATCH|DELETE)\b')
  def test_read_only_language(self): self.assertIn('backend-derived',self.js.lower()); self.assertIn('read-only',self.js.lower())
  def test_responsive(self): self.assertIn('@media(max-width:900px)',self.css)
if __name__=='__main__': unittest.main(verbosity=2)
