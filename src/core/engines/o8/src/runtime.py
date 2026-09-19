from .audit import AuditLog
from .sqlite_audit import SQLiteAuditLog
from .metrics import MetricsCollector, aggregate_runs
from .health import evaluate_health

class O8Runtime:
    def __init__(self, audit_path=None):
        self.audit = SQLiteAuditLog(audit_path) if audit_path else AuditLog()
        self.metrics=MetricsCollector()

    def start_run(self,run_id,project_id,request):
        return self.audit.append(run_id,"run_start","RECEIVED","orchestrator","STARTED",
                                 {"project_id":project_id,"request":request})

    def log_state(self,run_id,state,component="orchestrator",status="OK",**details):
        return self.audit.append(run_id,"state_change",state,component,status,details)

    def log_engine(self,run_id,engine_id,status,**details):
        return self.audit.append(run_id,"engine","RUNNING",engine_id,status,details)

    def log_tool(self,run_id,tool_id,status,**details):
        return self.audit.append(run_id,"tool","RUNNING",tool_id,status,details)

    def log_approval(self,run_id,status,approval_id,**details):
        state="AWAITING_APPROVAL" if status=="PENDING" else "RUNNING"
        return self.audit.append(run_id,"approval",state,"approval-controller",status,
                                 {"approval_id":approval_id,**details})

    def log_qa(self,run_id,status,**details):
        return self.audit.append(run_id,"qa","QA","qa-controller",status,details)

    def log_memory(self,run_id,status,**details):
        return self.audit.append(run_id,"memory","MEMORY_WRITE","memory-runtime",status,details)

    def end_run(self,run_id,status="COMPLETE",**details):
        state="RESPONDED" if status=="COMPLETE" else "FAILED"
        return self.audit.append(run_id,"run_end",state,"orchestrator",status,details)

    def run_summary(self,run_id):
        return self.metrics.summarize_run(run_id,self.audit.for_run(run_id))

    def close(self):
        close = getattr(self.audit, "close", None)
        if callable(close):
            close()

    def health(self,run_summaries):
        agg=aggregate_runs(run_summaries)
        return {"aggregate":agg,"health":evaluate_health(agg)}
