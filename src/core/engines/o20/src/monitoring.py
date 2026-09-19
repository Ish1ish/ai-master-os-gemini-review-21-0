class AutomationMonitoring:
    def build(self, workflow):
        return {
            "events": [
                "workflow_started",
                "trigger_received",
                "step_started",
                "step_completed",
                "approval_requested",
                "approval_resolved",
                "step_failed",
                "workflow_completed",
                "workflow_cancelled",
            ],
            "health_signals": [
                "success_rate",
                "failure_rate",
                "average_duration",
                "approval_rate",
                "retry_count",
                "stalled_runs",
            ],
            "audit_fields": [
                "run_id",
                "workflow_id",
                "workflow_version",
                "step_id",
                "tool_id",
                "status",
                "timestamp",
            ],
        }
