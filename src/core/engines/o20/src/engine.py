from .workflow import WorkflowBuilder
from .triggers import TriggerPlanner
from .tools import WorkflowToolPlanner
from .approval import AutomationApprovalGate
from .recovery import RecoveryPlanner
from .monitoring import AutomationMonitoring
from .qa import validate_automation_output


class RealAutomationEngine:
    def __init__(self):
        self.workflow=WorkflowBuilder()
        self.triggers=TriggerPlanner()
        self.tools=WorkflowToolPlanner()
        self.approvals=AutomationApprovalGate()
        self.recovery=RecoveryPlanner()
        self.monitoring=AutomationMonitoring()

    def build(self, process, trigger_spec=None):
        trigger_spec=trigger_spec or {"type": process.get("trigger","manual")}

        workflow=self.workflow.build(process)
        trigger_validation=self.triggers.validate(trigger_spec)
        tool_plan=self.tools.build(workflow["steps"])
        approvals=self.approvals.build(workflow["steps"])
        recovery=self.recovery.build(workflow["steps"])
        monitoring=self.monitoring.build(workflow)

        out={
            "status":"DRAFT",
            "engine_id":"E-11",
            "engine_version":"O20-v1.0",
            "workflow":workflow,
            "trigger":{
                "spec":trigger_spec,
                "validation":trigger_validation,
            },
            "tool_plan":tool_plan,
            "approval_gates":approvals,
            "recovery":recovery,
            "monitoring":monitoring,
            "sales_to_automation_handoff": process.get("sales_to_automation_handoff", {}),
        }

        qa=validate_automation_output(out)
        out["qa"]=qa

        if trigger_validation["status"] != "PASS":
            out["status"]="FAILED"
            out["failure_reason"]="invalid_trigger"
        else:
            out["status"]="COMPLETE" if qa["status"]=="PASS" else "FAILED"

        return out
