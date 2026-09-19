import tempfile
import threading
import unittest

from src.runtime_o37 import O37Runtime
from src.quota import TenantQuota


class TestO37(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.rt = O37Runtime(self.td.name)
        self.rt.provision_demo()

    def tearDown(self):
        self.rt.close()
        self.td.cleanup()

    def test_same_tenant_owner_allowed(self):
        p = self.rt.principal("user-a", "TENANT-A", ["viewer"])
        out = self.rt.tenants.project(p, "P-A")
        self.assertEqual(out["status"], "ALLOW")

    def test_cross_tenant_denied_and_target_hidden(self):
        p = self.rt.principal("user-a", "TENANT-A", ["viewer"])
        out = self.rt.tenants.project(p, "P-B")
        self.assertEqual(out["status"], "DENY")
        self.assertEqual(out["reason"], "cross_tenant_access")
        self.assertNotIn("project", out)

    def test_same_tenant_operator_allowed(self):
        p = self.rt.principal("operator-a", "TENANT-A", ["operator"])
        self.assertEqual(self.rt.tenants.project(p, "P-A2")["status"], "ALLOW")

    def test_same_tenant_non_owner_viewer_denied(self):
        p = self.rt.principal("user-z", "TENANT-A", ["viewer"])
        out = self.rt.tenants.project(p, "P-A")
        self.assertEqual(out["status"], "DENY")
        self.assertEqual(out["reason"], "project_ownership_required")

    def test_quota_is_tenant_scoped(self):
        p_a = self.rt.principal("user-a", "TENANT-A", ["viewer"])
        p_b = self.rt.principal("user-b", "TENANT-B", ["viewer"])
        for _ in range(5):
            self.assertEqual(self.rt.tenants.reserve_job(p_a, "P-A")["status"], "RESERVED")
        self.assertEqual(self.rt.tenants.reserve_job(p_a, "P-A")["status"], "QUOTA_EXCEEDED")
        self.assertEqual(self.rt.tenants.reserve_job(p_b, "P-B")["status"], "RESERVED")

    def test_missing_project_is_not_found(self):
        p = self.rt.principal("user-a", "TENANT-A", ["viewer"])
        self.assertEqual(self.rt.tenants.project(p, "NOPE")["status"], "NOT_FOUND")

    def test_global_admin_requires_explicit_cross_tenant_scope(self):
        no_scope = self.rt.principal("admin", "TENANT-A", ["admin"])
        self.assertEqual(self.rt.tenants.project(no_scope, "P-B")["status"], "DENY")
        with_scope = self.rt.principal("admin", "TENANT-A", ["admin"], ["tenant:cross"])
        self.assertEqual(self.rt.tenants.project(with_scope, "P-B")["status"], "ALLOW")

    def test_quota_release_does_not_underflow(self):
        out = self.rt.tenants.release_job("TENANT-A")
        self.assertEqual(out["active"], 0)

    def test_quota_concurrent_reservations_are_bounded(self):
        quota = TenantQuota(max_active_jobs=5, path=self.td.name + "/concurrent.sqlite3")
        results = []
        lock = threading.Lock()

        def reserve():
            out = quota.reserve("TENANT-A")
            with lock:
                results.append(out["status"])

        threads = [threading.Thread(target=reserve) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        quota.close()
        self.assertEqual(results.count("RESERVED"), 5)
        self.assertEqual(results.count("QUOTA_EXCEEDED"), 15)

    def test_close_is_idempotent(self):
        self.rt.close()
        self.rt.close()


if __name__ == "__main__":
    unittest.main()
