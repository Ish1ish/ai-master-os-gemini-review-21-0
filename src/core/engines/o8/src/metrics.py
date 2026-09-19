from datetime import datetime

class MetricsCollector:
    def summarize_run(self, run_id, events):
        run_events=[e for e in events if e["run_id"]==run_id]
        if not run_events:
            return {"run_id":run_id,"status":"NO_DATA"}
        times=[e["timestamp"] for e in run_events]
        start=datetime.fromisoformat(min(times))
        end=datetime.fromisoformat(max(times))
        failed=sum(1 for e in run_events if e["status"] in {"FAILED","ERROR","BLOCKED"})
        completed=any(e["event_type"]=="run_end" and e["status"]=="COMPLETE" for e in run_events)
        qa_pass_count=sum(1 for e in run_events if e["event_type"]=="qa" and e["status"]=="PASS")
        qa_fail_or_refine_count=sum(1 for e in run_events if e["event_type"]=="qa" and e["status"] in {"FAIL","REFINE"})
        qa_status="PASS" if qa_pass_count > 0 and qa_fail_or_refine_count == 0 else ("FAIL" if qa_fail_or_refine_count > 0 else "—")
        return {
            "run_id":run_id,
            "status":"COMPLETE" if completed and failed==0 else "ATTENTION",
            "duration_seconds":max(0.0,(end-start).total_seconds()),
            "event_count":len(run_events),
            "failure_count":failed,
            "tool_event_count":sum(1 for e in run_events if e["event_type"]=="tool"),
            "approval_event_count":sum(1 for e in run_events if e["event_type"]=="approval"),
            "qa_pass_count":qa_pass_count,
            "qa_fail_or_refine_count":qa_fail_or_refine_count,
            "qa_status":qa_status,
        }

def aggregate_runs(run_summaries):
    total=len(run_summaries)
    if total==0: return {"run_count":0,"success_rate":0.0,"failure_count":0}
    complete=sum(1 for x in run_summaries if x.get("status")=="COMPLETE")
    return {
        "run_count":total,
        "success_rate":complete/total,
        "failure_count":sum(x.get("failure_count",0) for x in run_summaries),
        "avg_duration_seconds":sum(x.get("duration_seconds",0) for x in run_summaries)/total,
    }
