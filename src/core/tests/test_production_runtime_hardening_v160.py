import os
import tempfile
import unittest

from src.jobs import JobStore
from src.handoff_contracts import semantic_core, validate_semantic_handoff
from src.service import ApplicationService


class _StubRuntime:
    class _Monitoring:
        def __init__(self): self.events=[]
        def start_run(self,*a,**k): self.events.append(("start",a))
        def end_run(self,*a,**k): self.events.append(("end",a,k))
        def log_state(self,*a,**k): self.events.append(("state",a,k))
    def __init__(self): self.monitoring=self._Monitoring(); self.calls=[]
    def run(self, run_id, project_id, request, audience=None, goal=None, constraints=None):
        self.calls.append((run_id, project_id, request, audience, goal, constraints))
        return {"status":"COMPLETE","run_id":run_id}
    def close(self): pass

class TestProductionRuntimeHardeningV160(unittest.TestCase):
    def test_job_submission_context_persists(self):
        with tempfile.TemporaryDirectory() as d:
            store=JobStore(os.path.join(d,"jobs.sqlite3"))
            store.create("J1","P1","R", audience="egyptian owners", goal="research", constraints=["low cost"])
            row=store.get("J1")
            self.assertEqual(row["audience"],"egyptian owners")
            self.assertEqual(row["goal"],"research")
            self.assertEqual(row["constraints"],["low cost"])
            store.close()


    def test_string_constraints_are_normalized_as_one_constraint(self):
        with tempfile.TemporaryDirectory() as d:
            store=JobStore(os.path.join(d,"jobs.sqlite3"))
            store.create("J1","P1","R", constraints="Use recent web information. Prefer low cost.")
            self.assertEqual(store.get("J1")["constraints"],["Use recent web information. Prefer low cost."])
            store.close()

    def test_concurrent_claim_is_single_owner(self):
        with tempfile.TemporaryDirectory() as d:
            s1=JobStore(os.path.join(d,"jobs.sqlite3"))
            s1.create("J1","P1","R")
            s2=JobStore(os.path.join(d,"jobs.sqlite3"))
            self.assertIsNotNone(s1.claim("J1"))
            self.assertIsNone(s2.claim("J1"))
            s1.close(); s2.close()

    def test_execute_uses_stored_submission_context(self):
        with tempfile.TemporaryDirectory() as d:
            rt=_StubRuntime()
            svc=ApplicationService(db_path=os.path.join(d,"jobs.sqlite3"),runtime=rt)
            out=svc.submit("P1","R",audience="Egyptian owners",goal="compare tools",constraints=["low cost"])
            svc.execute(out["job_id"], internal=True)
            self.assertEqual(rt.calls[0][3:],("Egyptian owners","compare tools",["low cost"]))
            svc.close()

    def test_execute_claim_prevents_second_run(self):
        with tempfile.TemporaryDirectory() as d:
            rt=_StubRuntime()
            svc=ApplicationService(db_path=os.path.join(d,"jobs.sqlite3"),runtime=rt)
            out=svc.submit("P1","R")
            first=svc.execute(out["job_id"],internal=True)
            second=svc.execute(out["job_id"],internal=True)
            self.assertEqual(first["status"],"COMPLETE")
            self.assertEqual(second["status"],"COMPLETE")
            self.assertEqual(len(rt.calls),1)
            svc.close()

    def test_operator_role_has_execute_scope(self):
        from src.rbac import RBAC
        scopes=RBAC().scopes_for_roles({"operator"})
        self.assertIn("run:execute", scopes)

    def test_semantic_core_removes_quick_answer_wrapper_and_raw_urls(self):
        self.assertEqual(semantic_core("Quick Answer: solve onboarding friction"),"solve onboarding friction")
        handoff={"handoff_type":"strategy_to_product","source_engine":"E-04","target_engine":"E-05","object_id":"X","source_refs":["S1"],"problem":"https://example.com | raw"}
        self.assertEqual(validate_semantic_handoff(handoff,contract="strategy_to_product_v1")["status"],"FAIL")

if __name__=="__main__": unittest.main()
