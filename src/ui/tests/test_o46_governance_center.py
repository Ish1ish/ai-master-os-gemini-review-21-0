import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HTML=(ROOT/"src/ui/ui/index.html").read_text(encoding="utf-8")
APP=(ROOT/"src/ui/ui/app.js").read_text(encoding="utf-8")
CSS=(ROOT/"src/ui/ui/styles.css").read_text(encoding="utf-8")

class TestO46GovernanceExperience(unittest.TestCase):
    def test_governance_hero_present(self):
        self.assertIn("governance-experience-hero",HTML)
        self.assertIn("AWAITING HUMAN DECISION",HTML)
    def test_live_approval_surface_preserved(self):
        self.assertIn("approvalList",HTML)
        self.assertIn("approvalInspector",HTML)
        self.assertIn("/approvals/pending",APP)
    def test_backend_authority_preserved(self):
        self.assertIn("The UI is not the policy authority",HTML)
        self.assertIn("Backend-authoritative · fail-closed",HTML)
    def test_risk_and_external_impact_are_exposed(self):
        for token in ("external_effect","governance-impact-grid","governance-decision-state"):
            self.assertIn(token,APP+CSS)
    def test_policy_and_binding_are_exposed(self):
        self.assertIn("policy_version",APP)
        self.assertIn("binding",APP)
    def test_approval_actions_remain_backend_bound(self):
        self.assertIn("/approvals/${encodeURIComponent(id)}/decision",APP)
        self.assertNotIn("fetch('/approve",APP)
    def test_no_local_auto_approval(self):
        self.assertNotIn("automaticApproval = true",APP)
        self.assertNotIn("autoApprove()",APP)
    def test_raw_payload_is_optional(self):
        self.assertIn("governance-raw-details",APP+CSS)
    def test_responsive(self):
        self.assertIn("@media(max-width:900px)",CSS)
        self.assertIn("@media(max-width:640px)",CSS)
    def test_rtl(self):
        self.assertIn(".rtl-mode .governance-experience-hero",CSS)
        self.assertIn(".rtl-mode .governance-decision-state",CSS)
    def test_human_gate_message(self):
        self.assertIn("Consequential actions stay behind an explicit human gate.",HTML)
    def test_no_execution_control_added(self):
        self.assertNotIn("governanceExecuteBtn",HTML)

if __name__=="__main__": unittest.main()
