import json
import os
import tempfile

from .control_service_o35 import O35ControlService
from .qa_o35 import validate_o35


def run_smoke():
    td=tempfile.TemporaryDirectory()
    svc=O35ControlService(td.name)
    executed={"count":0}

    first=svc.execute_consequential(
        "RUN-O35","publish_public_content",{"asset":"demo"},
        execute_fn=lambda: executed.update(count=executed["count"]+1) or {"ok":True},
        requested_by="system",
    )

    # The first call creates a pending approval and must not execute.
    before=svc.get_approval(first["approval_id"])
    blocked=svc.execute_consequential(
        "RUN-O35","publish_public_content",{"asset":"demo"},
        execute_fn=lambda: executed.update(count=executed["count"]+1) or {"ok":True},
    )

    approved=svc.decide(
        first["approval_id"],"APPROVED","operator-1","Validated release"
    )

    after=svc.execute_consequential(
        "RUN-O35","publish_public_content",{"asset":"demo"},
        execute_fn=lambda: executed.update(count=executed["count"]+1) or {"ok":True},
    )

    second=svc.execute_consequential(
        "RUN-O35","spend_ad_budget",{"amount":100},
        execute_fn=lambda: {"spent":True},
    )
    rejected=svc.decide(second["approval_id"],"REJECTED","operator-2","Budget not approved")
    rejected_execution=svc.execute_consequential(
        "RUN-O35","spend_ad_budget",{"amount":100},
        execute_fn=lambda: {"spent":True},
    )

    audits=svc.operator_store.list_actions(first["approval_id"])
    out={
        "pending_gate_status":first["status"],
        "before_approval_execution":blocked["status"],
        "approval_decision":approved["status"],
        "after_approval_execution":after["status"],
        "execution_count":executed["count"],
        "rejected_decision":rejected["status"],
        "rejected_execution":"BLOCKED" if rejected_execution["status"]=="BLOCKED" else rejected_execution["status"],
        "audit_status":"RECORDED" if audits else "MISSING",
    }
    out["qa"]=validate_o35(out)
    out["status"]="COMPLETE" if out["qa"]["status"]=="PASS" else "FAILED"
    svc.close()
    td.cleanup()
    return out
