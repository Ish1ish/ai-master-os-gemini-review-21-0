import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
UI=ROOT/'src'/'ui'/'ui'

class TestO46EvidenceExplorer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(UI/'index.html').read_text(encoding='utf-8')
        cls.js=(UI/'app.js').read_text(encoding='utf-8')
        cls.css=(UI/'styles.css').read_text(encoding='utf-8')
    def test_evidence_page_has_map(self):
        self.assertIn('evidence-map', self.html)
        self.assertIn('evidenceMapInspector', self.html)
    def test_map_renderer_present(self):
        self.assertIn('renderO46EvidenceMapV4', self.js)
        self.assertIn('data-evidence-node', self.js)
    def test_backend_derived_guardrails(self):
        self.assertIn('BACKEND DERIVED', self.js)
        self.assertIn('does not create sources', self.js)
    def test_claim_source_decision_flow(self):
        for token in ('Recommendation','Customer problem','Why this direction','Current decision'):
            self.assertIn(token,self.js)
    def test_conflict_confidence_metrics(self):
        for token in ('Conflicts','Confidence','research.conflicts','decision.confidence'):
            self.assertIn(token,self.js)
    def test_visual_contract(self):
        for token in ('.evidence-map-canvas','.evidence-link','.evidence-map-summary','.evidence-trace-head'):
            self.assertIn(token,self.css)
    def test_css_responsive(self):
        self.assertIn('@media(max-width:850px)',self.css)
    def test_ui4_identity(self):
        self.assertIn('UI-4 O46 Evidence Explorer 2.0',self.css)

if __name__=='__main__':
    unittest.main()
