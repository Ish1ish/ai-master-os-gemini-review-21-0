import uuid
import os
from .jobs import JobStore, normalize_constraints
from .policy import PolicyEngine
from .governance_intelligence import GovernanceIntelligence
from .health import HealthCheck
from .real_wiring import O23Runtime
from .providers import fake_model_provider, fake_search_provider
from .live_providers import model_provider, search_provider, provider_configuration_status
from .experiment_store import ExperimentStore
from .experiments import ExperimentService
from .decision_memory import CounterfactualDecisionMemory
from .adaptive_decision import AdaptiveDecisionIntelligence
from .auth import Authenticator


class ApplicationService:
    def __init__(self, db_path="./data/jobs.sqlite3",
                 runtime=None, authenticator=None, policy=None, experiments_db_path=None):
        production = __import__("os").getenv("AI_OS_ENV", "local").strip().lower() in {"prod", "production"}
        if runtime is not None:
            selected_runtime = runtime
        elif production:
            cfg = provider_configuration_status()
            if cfg["status"] != "CONFIGURED":
                raise RuntimeError("production provider configuration incomplete: " + ",".join(cfg["missing"]))
            selected_runtime = O23Runtime(
                model_provider=model_provider,
                search_provider=search_provider,
                memory_path=__import__("os").getenv("AI_OS_MEMORY_DB_PATH"),
                audit_path=__import__("os").getenv("AI_OS_AUDIT_DB_PATH"),
            )
        else:
            selected_runtime = O23Runtime(
                model_provider=fake_model_provider,
                search_provider=fake_search_provider,
                memory_path=None,
                audit_path=None,
            )
        self.jobs=JobStore(db_path)
        self.runtime=selected_runtime
        if authenticator is None:
            authenticator = Authenticator(
                production=production,
                allow_local_bypass=not production,
            )
        self.auth=authenticator
        experiment_path = experiments_db_path or __import__("os").getenv("AI_OS_EXPERIMENTS_DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(db_path)), "experiments.sqlite3")
        self.experiments=ExperimentService(ExperimentStore(experiment_path), self.jobs, memory_runtime=getattr(selected_runtime, "memory", None))
        governance_path = os.getenv("AI_OS_GOVERNANCE_DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(db_path)), "governance.sqlite3")
        self.governance=GovernanceIntelligence(governance_path)
        if hasattr(self.runtime, "set_approval_requester"):
            self.runtime.set_approval_requester(self._request_runtime_approval)
        from .counterfactual_preflight import CounterfactualPreflight
        from .counterfactual_delta import CounterfactualDelta
        self.counterfactual=CounterfactualPreflight(self.governance)
        self.counterfactual_delta=CounterfactualDelta()
        if db_path == ":memory:":
            memory_path = os.getenv("AI_OS_COUNTERFACTUAL_MEMORY_DB_PATH") or ":memory:"
        else:
            memory_path = os.getenv("AI_OS_COUNTERFACTUAL_MEMORY_DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(db_path)), "counterfactual_memory.sqlite3")
        self.counterfactual_memory = CounterfactualDecisionMemory(memory_path)
        self.adaptive_decision = AdaptiveDecisionIntelligence(self.counterfactual_memory)
        self.policy=policy or PolicyEngine(allowed_scopes={"read_knowledge","read_web","generate_content","write_memory","read_memory","audit_write","request_approval","run:submit","run:read","run:list","run:execute","run:cancel","experiment:read","experiment:write","experiment:evaluate","learning:read","governance:read","governance:evaluate","approval:read","approval:decide","counterfactual:record","counterfactual:observe","counterfactual:read"})
        self.health=HealthCheck()
        self._closed=False

    def simulate_counterfactual(self, body=None, credentials=None):
        body = dict(body or {})
        gate = self._authorize(credentials, "simulate_counterfactual", "governance:evaluate")
        if gate["status"] != "ALLOW":
            return gate
        project_id = str(body.get("project_id") or "").strip()
        requested_by = str(body.get("requested_by") or "").strip()
        actions = body.get("actions")
        context = body.get("context") or {}
        return self.counterfactual.simulate(
            project_id=project_id,
            requested_by=requested_by,
            actions=actions,
            context=context,
        )

    def compare_counterfactual(self, body=None, credentials=None):
        body = dict(body or {})
        gate = self._authorize(credentials, "compare_counterfactual", "governance:evaluate")
        if gate["status"] != "ALLOW":
            return gate
        baseline = body.get("baseline")
        candidate = body.get("candidate")
        return self.counterfactual_delta.compare(baseline, candidate)

    def record_counterfactual_prediction(self, body=None, credentials=None):
        body = dict(body or {})
        gate = self._authorize(credentials, "record_counterfactual_prediction", "counterfactual:record")
        if gate["status"] != "ALLOW":
            return gate
        return self.counterfactual_memory.record_prediction(
            project_id=str(body.get("project_id") or "").strip(),
            requested_by=str(body.get("requested_by") or "").strip(),
            prediction=body.get("prediction") or {},
        )

    def observe_counterfactual_outcome(self, body=None, credentials=None):
        body = dict(body or {})
        gate = self._authorize(credentials, "observe_counterfactual_outcome", "counterfactual:observe")
        if gate["status"] != "ALLOW":
            return gate
        return self.counterfactual_memory.observe_outcome(
            prediction_id=str(body.get("prediction_id") or "").strip(),
            actual=body.get("actual") or {},
        )

    def get_adaptive_decision(self, body=None, credentials=None):
        body = dict(body or {})
        gate = self._authorize(credentials, "read_adaptive_decision", "counterfactual:read")
        if gate["status"] != "ALLOW":
            return gate
        project_id = str(body.get("project_id") or "").strip()
        if not project_id:
            return {"status": "BLOCK", "reason": "project_id_required"}
        return self.adaptive_decision.advise_for_project(
            project_id,
            candidate_decision=body.get("candidate_decision"),
            candidate_risk=body.get("candidate_risk"),
            limit=int(body.get("limit") or 50),
        )

    def get_counterfactual_memory(self, project_id, credentials=None):
        gate = self._authorize(credentials, "read_counterfactual_memory", "counterfactual:read")
        if gate["status"] != "ALLOW":
            return gate
        return self.counterfactual_memory.calibration_context(str(project_id or "").strip())

    def _authorize(self, credentials, action, scope):
        auth=self.auth.authenticate(credentials)
        if auth.get("status") not in {"ALLOW","BYPASS_FOR_LOCAL"}:
            return {"status":"UNAUTHORIZED","auth":auth}
        if scope not in auth.get("scopes",[]):
            return {"status":"FORBIDDEN","reason":"scope_missing","scope":scope}
        decision=self.policy.authorize(action,scope,external_effect=False)
        if decision["status"]!="ALLOW":
            return {"status":"FORBIDDEN","policy":decision}
        return {"status":"ALLOW","auth":auth}

    def _request_runtime_approval(self, *, run_id, project_id, action, context):
        decision=self.governance.evaluate(
            project_id=project_id,
            action=action,
            context=context,
            run_id=run_id,
            requested_by="orchestrator",
            create_approval=True,
        )
        approval=decision.get("approval") or {}
        approval_id=approval.get("approval_id") or decision.get("approval_id")
        if decision.get("decision") == "REVIEW" and approval_id:
            request={
                "approval_id": approval_id,
                "run_id": run_id,
                "action": action,
                "risk": decision.get("risk"),
                "reason": "Human approval required before consequential action: %s (risk=%s)." % (action, decision.get("risk")),
                "context": context,
                "requested_by": approval.get("requested_by", "orchestrator"),
                "status": approval.get("status", "PENDING"),
                "decision_by": approval.get("decided_by"),
                "decision_reason": approval.get("decision_reason"),
                "created_at": approval.get("created_at"),
            }
            return {
                "status": approval.get("status", "PENDING"),
                "risk": decision.get("risk"),
                "approval_id": approval_id,
                "run_state": "AWAITING_APPROVAL",
                "request": request,
            }
        return {
            "status": decision.get("decision", "BLOCK"),
            "risk": decision.get("risk"),
            "approval_id": approval_id,
            "run_state": "RUNNING" if decision.get("execution_allowed") else "BLOCKED",
        }

    def submit(self, project_id, request, audience="small businesses using AI tools",
               goal="validate a lean business opportunity",
               constraints=None, language="en", credentials=None, internal=False):
        gate={"status":"ALLOW"} if internal else self._authorize(credentials,"submit_run","run:submit")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}

        job_id=f"JOB-{uuid.uuid4().hex[:12].upper()}"
        self.jobs.create(job_id,project_id,request,audience=audience,goal=goal,constraints=constraints,language=language)
        return {
            "status":"QUEUED",
            "job_id":job_id,
            "project_id":project_id,
            "run_id":job_id,
        }

    def _runtime_end_failed(self, job_id, reason=None):
        monitor=getattr(self.runtime, "monitoring", None)
        if monitor is None:
            return
        try:
            if reason:
                monitor.log_state(job_id, "FAILED", component="orchestrator", status="FAIL", reason=str(reason))
            monitor.end_run(job_id, "FAILED", reason=str(reason or "runtime_failed"))
        except Exception:
            pass

    def execute(self, job_id, audience=None, goal=None, constraints=None, language=None, credentials=None, internal=False):
        if self.auth and not internal:
            gate=self._authorize(credentials,"execute_run","run:execute")
            if gate["status"]!="ALLOW":
                return {"status":gate["status"],"error":gate,"job_id":job_id}

        job=self.jobs.get(job_id)
        if not job:
            return {"status":"NOT_FOUND","job_id":job_id}

        if job["status"] in {"COMPLETE","FAILED","CANCELLED","RUNNING"}:
            return job

        claimed=self.jobs.claim(job_id)
        if not claimed:
            return self.jobs.get(job_id) or {"status":"NOT_FOUND","job_id":job_id}

        # Stored submission context is the source of truth; execute callers may only override
        # context explicitly when an internal worker is processing a durable queue envelope.
        exec_audience=audience if audience is not None else claimed.get("audience")
        exec_goal=goal if goal is not None else claimed.get("goal")
        exec_constraints=constraints if constraints is not None else claimed.get("constraints")
        exec_constraints = normalize_constraints(exec_constraints)
        exec_language = language if language is not None else claimed.get("language","en")
        monitor_started=False
        try:
            monitor=getattr(self.runtime, "monitoring", None)
            if monitor is not None:
                monitor.start_run(job_id,claimed["project_id"],claimed["request"])
                monitor_started=True
            try:
                result=self.runtime.run(
                    job_id,claimed["project_id"],claimed["request"],
                    audience=exec_audience,goal=exec_goal,constraints=exec_constraints,language=exec_language
                )
            except TypeError as exc:
                # Preserve backward compatibility for test/dummy runtimes that predate language support.
                if "language" not in str(exc):
                    raise
                result=self.runtime.run(
                    job_id,claimed["project_id"],claimed["request"],
                    audience=exec_audience,goal=exec_goal,constraints=exec_constraints
                )
            if result.get("status")=="COMPLETE":
                self.jobs.set_status(job_id,"COMPLETE",result=result)
            else:
                error={
                    "failed_stage":result.get("failed_stage"),
                    "runtime_status":result.get("status"),
                    "error":result.get("error"),
                    "handoff_qa":result.get("handoff_qa"),
                    "handoff_chain_qa":result.get("handoff_chain_qa"),
                }
                self.jobs.set_status(job_id,"FAILED",error=error)
                if monitor_started:
                    self._runtime_end_failed(job_id,result.get("failed_stage") or result.get("status"))
        except Exception as exc:
            self.jobs.set_status(job_id,"FAILED",error={
                "type":type(exc).__name__,"message":str(exc),
            })
            if monitor_started:
                self._runtime_end_failed(job_id,str(exc))
        return self.jobs.get(job_id)

    def list_runs(self, limit=50, credentials=None):
        gate=self._authorize(credentials,"list_runs","run:list")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate,"runs":[]}
        return {"status":"OK","runs":self.jobs.list(limit)}

    def get_status(self, job_id, credentials=None):
        gate=self._authorize(credentials,"read_run","run:read")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}
        job=self.jobs.get(job_id)
        return {"status":"NOT_FOUND","job_id":job_id} if not job else job

    def cancel(self, job_id, credentials=None):
        gate=self._authorize(credentials,"cancel_run","run:cancel")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}
        job=self.jobs.get(job_id)
        if not job:
            return {"status":"NOT_FOUND","job_id":job_id}
        if job["status"]=="QUEUED":
            self.jobs.set_status(job_id,"CANCELLED")
            return self.jobs.get(job_id)
        return {"status":"CONFLICT","reason":"job_not_cancellable_in_current_state","current_status":job["status"]}

    def create_experiment_from_run(self, run_id, credentials=None):
        gate=self._authorize(credentials,"create_experiment","experiment:write")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}
        return self.experiments.create_from_run(run_id)

    def list_experiments(self, project_id=None, limit=50, credentials=None):
        gate=self._authorize(credentials,"list_experiments","experiment:read")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate,"experiments":[]}
        return self.experiments.list(project_id=project_id, limit=limit)

    def get_experiment(self, experiment_id, credentials=None):
        gate=self._authorize(credentials,"read_experiment","experiment:read")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}
        return self.experiments.get(experiment_id)

    def record_experiment_evidence(self, experiment_id, evidence, credentials=None):
        gate=self._authorize(credentials,"record_experiment_evidence","experiment:write")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}
        return self.experiments.record_evidence(experiment_id, evidence)

    def get_learning_context(self, project_id, current_experiment_id=None, credentials=None):
        gate=self._authorize(credentials,"read_learning_context","learning:read")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}
        return self.experiments.get_learning_context(project_id, current_experiment_id=current_experiment_id)

    def evaluate_experiment(self, experiment_id, credentials=None):
        gate=self._authorize(credentials,"evaluate_experiment","experiment:evaluate")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}
        return self.experiments.evaluate(experiment_id)

    def evaluate_governance(self, project_id, action, context=None, run_id=None, credentials=None, create_approval=True):
        gate=self._authorize(credentials,"evaluate_governance","governance:evaluate")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}
        auth=gate.get("auth") or {}
        requested_by=auth.get("principal") or "system"
        return self.governance.evaluate(project_id, action, context=context, run_id=run_id, requested_by=requested_by, create_approval=create_approval)

    def list_governance_decisions(self, project_id=None, run_id=None, limit=50, credentials=None):
        gate=self._authorize(credentials,"list_governance_decisions","governance:read")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate,"decisions":[]}
        return {"status":"OK","decisions":self.governance.list(project_id=project_id, run_id=run_id, limit=limit)}

    def get_governance_decision(self, decision_id, credentials=None):
        gate=self._authorize(credentials,"read_governance_decision","governance:read")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}
        return self.governance.get(decision_id)

    def list_pending_approvals(self, project_id=None, credentials=None):
        gate=self._authorize(credentials,"list_pending_approvals","approval:read")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate,"approvals":[]}
        return {"status":"OK","approvals":self.governance.pending(project_id)}

    def get_approval(self, approval_id, credentials=None):
        gate=self._authorize(credentials,"get_approval","approval:read")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}
        out=self.governance.approvals.get(approval_id)
        return out or {"status":"NOT_FOUND","approval_id":approval_id}

    def decide_approval(self, approval_id, decision, reason="", credentials=None):
        gate=self._authorize(credentials,"decide_approval","approval:decide")
        if gate["status"]!="ALLOW":
            return {"status":gate["status"],"error":gate}
        auth=gate.get("auth") or {}
        roles=auth.get("roles") or []
        if not ({"approver","admin"} & set(roles)):
            return {"status":"FORBIDDEN","reason":"approval_authority_required"}
        principal={"principal_id":auth.get("principal"),"roles":roles}
        return self.governance.decide(approval_id, principal, decision, reason)

    def readiness(self):
        return self.health.check({
            "job_store":"UP",
            "runtime":"UP",
            "policy":"READY",
            "health_check":"READY",
        })


    def close(self):
        if self._closed:
            return
        try:
            self.counterfactual_memory.close()
        except Exception:
            pass
        self._closed=True
        try:
            if hasattr(self.jobs, "close"):
                self.jobs.close()
            if hasattr(self, "experiments") and hasattr(self.experiments, "store"):
                self.experiments.store.close()
            if hasattr(self, "governance"):
                self.governance.close()
        finally:
            close_runtime = getattr(self.runtime, "close", None)
            if callable(close_runtime):
                close_runtime()

    def __enter__(self):
        if self._closed:
            raise RuntimeError("ApplicationService is closed")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
