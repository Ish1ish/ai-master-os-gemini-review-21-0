import json
import tempfile

from src.runtime_o37 import O37Runtime


def run_smoke():
    td = tempfile.TemporaryDirectory()
    try:
        rt = O37Runtime(td.name)
        rt.provision_demo()
        user_a = rt.principal("user-a", "TENANT-A", ["viewer"])
        user_b = rt.principal("user-b", "TENANT-B", ["viewer"])
        operator_a = rt.principal("operator-a", "TENANT-A", ["operator"])
        admin_global = rt.principal("admin", "TENANT-A", ["admin"], ["tenant:cross"])

        same = rt.tenants.project(user_a, "P-A")
        cross = rt.tenants.project(user_a, "P-B")
        operator = rt.tenants.project(operator_a, "P-A2")
        missing = rt.tenants.project(user_a, "NOPE")
        reserve_a = [rt.tenants.reserve_job(user_a, "P-A") for _ in range(5)]
        reserve_a_over = rt.tenants.reserve_job(user_a, "P-A")
        reserve_b = rt.tenants.reserve_job(user_b, "P-B")
        admin = rt.tenants.project(admin_global, "P-B")
        rt.close()
        return {
            "same_tenant": same,
            "cross_tenant": cross,
            "operator_same_tenant": operator,
            "missing_project": missing,
            "tenant_a_reserved": sum(x.get("status") == "RESERVED" for x in reserve_a),
            "tenant_a_over_quota": reserve_a_over,
            "tenant_b_independent_reservation": reserve_b,
            "global_admin_override": admin,
            "status": "COMPLETE"
            if same["status"] == "ALLOW"
            and cross["status"] == "DENY"
            and operator["status"] == "ALLOW"
            and missing["status"] == "NOT_FOUND"
            and reserve_a_over["status"] == "QUOTA_EXCEEDED"
            and reserve_b["status"] == "RESERVED"
            and admin["status"] == "ALLOW"
            else "FAIL",
        }
    finally:
        td.cleanup()


if __name__ == "__main__":
    out = run_smoke()
    print(json.dumps(out, indent=2, ensure_ascii=False))
    raise SystemExit(0 if out.get("status") == "COMPLETE" else 1)
