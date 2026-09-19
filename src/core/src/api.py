from .service import ApplicationService


class InProcessAPI:
    """
    Transport-neutral service facade.
    A real HTTP framework can wrap these handlers without changing the service contract.
    """

    def __init__(self, service=None):
        self.service=service or ApplicationService()

    def health(self):
        return {"status":"OK"}

    def readiness(self):
        return self.service.readiness()

    def post_run(self, body, credentials=None):
        required=["project_id","request"]
        missing=[k for k in required if not body.get(k)]
        if missing:
            return {"status":"BAD_REQUEST","missing":missing}
        return self.service.submit(
            project_id=body["project_id"],
            request=body["request"],
            audience=body.get("audience","small businesses using AI tools"),
            goal=body.get("goal","validate a lean business opportunity"),
            constraints=body.get("constraints"),
            language=body.get("language", body.get("output_language", "en")),
            credentials=credentials,
        )

    def run_now(self, job_id, body=None, credentials=None):
        body=body or {}
        return self.service.execute(
            job_id,
            audience=body.get("audience"),
            goal=body.get("goal"),
            constraints=body.get("constraints"),
            language=body.get("language", body.get("output_language")),
            credentials=credentials,
        )


    def list_runs(self, limit=50, credentials=None):
        return self.service.list_runs(limit=limit, credentials=credentials)

    def get_run(self, job_id, credentials=None):
        return self.service.get_status(job_id,credentials)

    def cancel_run(self, job_id, credentials=None):
        return self.service.cancel(job_id,credentials)


    def list_experiments(self, project_id=None, limit=50, credentials=None):
        return self.service.list_experiments(project_id=project_id, limit=limit, credentials=credentials)

    def get_experiment(self, experiment_id, credentials=None):
        return self.service.get_experiment(experiment_id, credentials=credentials)

    def create_experiment_from_run(self, run_id, credentials=None):
        return self.service.create_experiment_from_run(run_id, credentials=credentials)

    def record_experiment_evidence(self, experiment_id, body=None, credentials=None):
        return self.service.record_experiment_evidence(experiment_id, body or {}, credentials=credentials)

    def get_learning_context(self, project_id, current_experiment_id=None, credentials=None):
        return self.service.get_learning_context(project_id, current_experiment_id=current_experiment_id, credentials=credentials)

    def evaluate_experiment(self, experiment_id, credentials=None):
        return self.service.evaluate_experiment(experiment_id, credentials=credentials)

    def compare_counterfactual(self, body=None, credentials=None):
        return self.service.compare_counterfactual(body, credentials)

    def record_counterfactual_prediction(self, body=None, credentials=None):
        return self.service.record_counterfactual_prediction(body or {}, credentials)

    def observe_counterfactual_outcome(self, body=None, credentials=None):
        return self.service.observe_counterfactual_outcome(body or {}, credentials)

    def get_adaptive_decision(self, body=None, credentials=None):
        return self.service.get_adaptive_decision(body or {}, credentials)

    def get_counterfactual_memory(self, project_id, credentials=None):
        return self.service.get_counterfactual_memory(project_id, credentials)

    def simulate_counterfactual(self, body=None, credentials=None):
        return self.service.simulate_counterfactual(body or {}, credentials)

    def evaluate_governance(self, body=None, credentials=None):
        body=body or {}
        if not body.get("project_id") or not body.get("action"):
            return {"status":"BAD_REQUEST","missing":[k for k in ("project_id","action") if not body.get(k)]}
        return self.service.evaluate_governance(
            project_id=body["project_id"], action=body["action"], context=body.get("context") or {},
            run_id=body.get("run_id"), credentials=credentials, create_approval=body.get("create_approval", True),
        )

    def list_governance_decisions(self, project_id=None, run_id=None, limit=50, credentials=None):
        return self.service.list_governance_decisions(project_id, run_id, limit, credentials)

    def get_governance_decision(self, decision_id, credentials=None):
        return self.service.get_governance_decision(decision_id, credentials)

    def list_pending_approvals(self, project_id=None, credentials=None):
        return self.service.list_pending_approvals(project_id, credentials)

    def get_approval(self, approval_id, credentials=None):
        return self.service.get_approval(approval_id, credentials)

    def decide_approval(self, approval_id, body=None, credentials=None):
        body=body or {}
        return self.service.decide_approval(approval_id, body.get("decision"), body.get("reason",""), credentials)
