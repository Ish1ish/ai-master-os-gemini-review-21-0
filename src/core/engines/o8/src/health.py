def evaluate_health(summary, thresholds=None):
    thresholds=thresholds or {"max_failure_rate":0.10,"max_avg_duration_seconds":120.0}
    runs=summary.get("run_count",0)
    success=summary.get("success_rate",0.0)
    failure_rate=(1.0-success) if runs else 0.0
    avg=summary.get("avg_duration_seconds",0.0)
    alerts=[]
    if runs and failure_rate>thresholds["max_failure_rate"]:
        alerts.append({"type":"HIGH_FAILURE_RATE","value":failure_rate,"threshold":thresholds["max_failure_rate"]})
    if avg>thresholds["max_avg_duration_seconds"]:
        alerts.append({"type":"HIGH_LATENCY","value":avg,"threshold":thresholds["max_avg_duration_seconds"]})
    return {"status":"HEALTHY" if not alerts else "DEGRADED","alerts":alerts,
            "failure_rate":failure_rate,"avg_duration_seconds":avg}
