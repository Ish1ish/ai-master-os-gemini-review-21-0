def classify_memory_event(run_result):
    events=[]
    pid=run_result.get("project_id","UNKNOWN")
    rid=run_result.get("run_id","UNKNOWN")

    decision=run_result.get("decision")
    if decision:
        events.append({
            "object_type":"Decision",
            "object_id":decision.get("decision_id", f"DEC-{rid}"),
            "version":decision.get("version","v1.0"),
            "project_id":pid,
            "summary":decision.get("summary",""),
            "scope":"project",
            "confidence":decision.get("confidence","medium"),
            "source_refs":decision.get("source_refs",[]),
            "status":"active",
        })

    experiment=run_result.get("experiment")
    if experiment and experiment.get("status")=="concluded":
        events.append({
            "object_type":"Experiment",
            "object_id":experiment.get("experiment_id",f"EXP-{rid}"),
            "version":experiment.get("version","v1.0"),
            "project_id":pid,
            "summary":experiment.get("learning",""),
            "scope":"project",
            "confidence":experiment.get("confidence","medium"),
            "source_refs":experiment.get("source_refs",[]),
            "status":"active",
        })

    insight=run_result.get("customer_insight")
    if insight:
        events.append({
            "object_type":"CustomerInsight",
            "object_id":insight.get("insight_id",f"INS-{rid}"),
            "version":insight.get("version","v1.0"),
            "project_id":pid,
            "summary":insight.get("summary",""),
            "scope":insight.get("scope","audience"),
            "confidence":insight.get("confidence","medium"),
            "source_refs":insight.get("source_refs",[]),
            "status":"active",
        })

    asset=run_result.get("approved_asset")
    if asset and asset.get("approved") is True:
        events.append({
            "object_type":"ApprovedAsset",
            "object_id":asset.get("asset_id",f"AST-{rid}"),
            "version":asset.get("version","v1.0"),
            "project_id":pid,
            "summary":asset.get("summary",""),
            "scope":"project",
            "confidence":"high",
            "source_refs":asset.get("source_refs",[]),
            "status":"active",
        })
    return {"events":events}
