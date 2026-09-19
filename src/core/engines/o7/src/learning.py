def build_learning_record(run_result, qa_result=None):
    if not any(run_result.get(k) for k in ("outcome","decision","experiment","learning")):
        return None
    decision=run_result.get("decision") or {}
    experiment=run_result.get("experiment") or {}
    return {
        "lesson_id": run_result.get("lesson_id", f"LES-{run_result.get('run_id','UNKNOWN')}"),
        "version": run_result.get("lesson_version","v1.0"),
        "project_id": run_result.get("project_id","UNKNOWN"),
        "summary": run_result.get("learning") or decision.get("summary") or experiment.get("learning") or str(run_result.get("outcome")),
        "scope":"project",
        "confidence":run_result.get("confidence") or decision.get("confidence") or experiment.get("confidence") or "medium",
        "source_refs":run_result.get("source_refs",[]),
        "qa_status":(qa_result or {}).get("status","UNKNOWN"),
        "status":"active",
    }
