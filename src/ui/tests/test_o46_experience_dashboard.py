import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui"

class TestO46ExecutiveDashboard(unittest.TestCase):
    def setUp(self):
        self.html=(UI/"index.html").read_text(encoding="utf-8")
        self.app=(UI/"app.js").read_text(encoding="utf-8")
        self.css=(UI/"styles.css").read_text(encoding="utf-8")
        self.exp=(UI/"experience.js").read_text(encoding="utf-8")
        self.schema=json.loads((ROOT/"contracts"/"o46_experience_view.schema.json").read_text(encoding="utf-8"))

    def test_executive_dashboard_shell_present(self):
        for token in ["o46ExecutiveDashboard","executiveRecommendation","executiveEvidenceCount","executiveNextAction"]:
            self.assertIn(token,self.html)

    def test_dashboard_reads_canonical_experience_fields(self):
        for token in ["view.decision.recommendation","view.decision.why","view.research.evidence_count","view.governance.status","view.next_step.recommendation"]:
            self.assertIn(token,self.app)

    def test_dashboard_exposes_explainability_action(self):
        self.assertIn("executiveDecisionBtn",self.app)
        self.assertIn("scrollIntoView",self.app)

    def test_dashboard_visual_system_present(self):
        for token in [".executive-recommendation",".executive-kpis",".score-orbit",".executive-next"]:
            self.assertIn(token,self.css)

    def test_experience_version_bumped(self):
        self.assertIn("O46_EXPERIENCE_DASHBOARD_BUILD = '1.1.0'",self.exp)

    def test_contract_has_required_sections(self):
        required={"run","intent","research","decision","governance","approval","execution","outcome","learning","next_step","provenance"}
        props=set(self.schema.get("properties",{}))
        self.assertTrue(required.issubset(props))

if __name__ == "__main__":
    unittest.main()
