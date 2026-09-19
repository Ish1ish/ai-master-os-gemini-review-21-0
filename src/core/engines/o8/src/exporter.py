import json
from pathlib import Path

def export_audit(log,path):
    Path(path).write_text(json.dumps(log.all(),indent=2),encoding="utf-8")
    return path

def export_run_report(run_id,log,metrics,path):
    events=log.for_run(run_id)
    report={"run_id":run_id,"summary":metrics.summarize_run(run_id,events),"events":events}
    Path(path).write_text(json.dumps(report,indent=2),encoding="utf-8")
    return path
