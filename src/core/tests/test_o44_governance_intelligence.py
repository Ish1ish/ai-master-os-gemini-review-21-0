import os
import tempfile
import unittest

from src.governance_intelligence import GovernanceIntelligence


class TestO44GovernanceIntelligence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.g = GovernanceIntelligence(os.path.join(self.tmp.name, "governance.sqlite3"))

    def tearDown(self):
        self.g.close()
        self.tmp.cleanup()

    def ctx(self, **extra):
        base = {
            "project_id": "PROJ-001",
            "confidence": "high",
            "evidence_refs": ["SRC-001", "SRC-002"],
            "evidence_boundary": "local_evidence_supported",
        }
        base.update(extra)
        return base

    def test_unknown_action_fails_closed(self):
        out = self.g.classify("do_anything", self.ctx())
        self.assertEqual(out["decision"], "BLOCK")
        self.assertFalse(out["execution_allowed"])

    def test_low_risk_high_confidence_auto_allows(self):
        out = self.g.classify("read_only_inspection", self.ctx())
        self.assertEqual(out["decision"], "AUTO_ALLOW")
        self.assertTrue(out["execution_allowed"])
        self.assertFalse(out["approval_required"])

    def test_external_action_requires_review(self):
        out = self.g.classify("publish_public_content", self.ctx())
        self.assertEqual(out["decision"], "REVIEW")
        self.assertTrue(out["approval_required"])
        self.assertFalse(out["execution_allowed"])
        self.assertEqual(out["risk"], "HIGH")

    def test_financial_action_requires_review(self):
        out = self.g.classify("spend_ad_budget", self.ctx())
        self.assertEqual(out["decision"], "REVIEW")
        self.assertTrue(out["financial"])

    def test_low_confidence_cannot_auto_allow(self):
        out = self.g.classify("read_only_inspection", self.ctx(confidence="low"))
        self.assertEqual(out["decision"], "REVIEW")
        self.assertEqual(out["reason_code"], "low_confidence")

    def test_missing_evidence_cannot_auto_allow(self):
        out = self.g.classify("read_only_inspection", self.ctx(evidence_refs=[]))
        self.assertEqual(out["decision"], "REVIEW")
        self.assertFalse(out["evidence_ready"])

    def test_sensitive_medium_action_reviews(self):
        out = self.g.classify("write_memory", self.ctx())
        self.assertEqual(out["decision"], "REVIEW")

    def test_review_creates_persistent_approval(self):
        out = self.g.evaluate("PROJ-001", "publish_public_content", self.ctx(), run_id="JOB-001", requested_by="operator-01")
        self.assertEqual(out["decision"], "REVIEW")
        self.assertIsNotNone(out["approval_id"])
        self.assertEqual(out["approval"]["status"], "PENDING")
        pending = self.g.pending("PROJ-001")
        self.assertEqual(len(pending), 1)

    def test_self_approval_is_denied(self):
        out = self.g.evaluate("PROJ-001", "publish_public_content", self.ctx(), run_id="JOB-002", requested_by="approver-01")
        decision = self.g.decide(out["approval_id"], {"principal_id": "approver-01", "roles": ["approver"]}, "APPROVED", "self test")
        self.assertEqual(decision["status"], "DENY")
        self.assertEqual(decision["reason"], "self_approval_not_allowed")

    def test_approved_by_different_approver(self):
        out = self.g.evaluate("PROJ-001", "publish_public_content", self.ctx(), run_id="JOB-003", requested_by="operator-01")
        decision = self.g.decide(out["approval_id"], {"principal_id": "approver-01", "roles": ["approver"]}, "APPROVED", "reviewed")
        self.assertEqual(decision["status"], "APPROVED")

    def test_non_approver_cannot_decide(self):
        out = self.g.evaluate("PROJ-001", "publish_public_content", self.ctx(), run_id="JOB-004", requested_by="operator-01")
        decision = self.g.decide(out["approval_id"], {"principal_id": "viewer-01", "roles": ["viewer"]}, "APPROVED")
        self.assertEqual(decision["status"], "DENY")
        self.assertEqual(decision["reason"], "approver_role_required")

    def test_decision_persists(self):
        out = self.g.evaluate("PROJ-001", "read_only_inspection", self.ctx(), run_id="JOB-005", requested_by="operator-01", create_approval=False)
        saved = self.g.get(out["decision_id"])
        self.assertEqual(saved["decision"], "AUTO_ALLOW")
        listed = self.g.list(project_id="PROJ-001", run_id="JOB-005")
        self.assertEqual(len(listed), 1)

    def test_review_is_a_policy_decision_not_execution(self):
        out = self.g.evaluate("PROJ-001", "send_external_message", self.ctx(), create_approval=False)
        self.assertFalse(out["execution_allowed"])
        self.assertTrue(out["approval_required"])


if __name__ == "__main__":
    unittest.main()

class TestO44RBAC(unittest.TestCase):
    def test_operator_can_evaluate_governance(self):
        from src.rbac import RBAC
        self.assertIn("governance:evaluate", RBAC().scopes_for_roles({"operator"}))

    def test_approver_can_read_governance(self):
        from src.rbac import RBAC
        self.assertIn("governance:read", RBAC().scopes_for_roles({"approver"}))

class TestO44HTTPAPI(unittest.TestCase):
    def test_governance_http_surface_roundtrip(self):
        import os, tempfile, threading, time
        from http.client import HTTPConnection
        from src.api import InProcessAPI
        from src.http_server import O32HTTPServer
        from src.service import ApplicationService
        with tempfile.TemporaryDirectory() as td:
            service = ApplicationService(db_path=os.path.join(td, "jobs.sqlite3"))
            api = InProcessAPI(service)
            server = O32HTTPServer(api, host="127.0.0.1", port=0, require_auth=False)
            port = server.server.server_address[1]
            t = threading.Thread(target=server.start, daemon=True); t.start(); time.sleep(0.05)
            try:
                conn = HTTPConnection("127.0.0.1", port, timeout=5)
                body = '{"project_id":"HTTP-O44","action":"publish_public_content","context":{"confidence":"high","evidence_boundary":"local_evidence_supported","evidence_refs":["SRC-1","SRC-2"]}}'
                conn.request("POST", "/governance/evaluate", body, {"Content-Type":"application/json"})
                resp = conn.getresponse(); payload = resp.read().decode()
                self.assertEqual(resp.status, 200)
                self.assertIn('"decision": "REVIEW"', payload)
                conn.request("GET", "/approvals/pending?project_id=HTTP-O44")
                resp2 = conn.getresponse(); payload2 = resp2.read().decode()
                self.assertEqual(resp2.status, 200)
                self.assertIn('HTTP-O44', payload2)
                conn.close()
            finally:
                server.shutdown(); service.close(); t.join(timeout=2)
