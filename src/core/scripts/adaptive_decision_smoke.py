import os, tempfile
from src.decision_memory import CounterfactualDecisionMemory
from src.adaptive_decision import AdaptiveDecisionIntelligence

with tempfile.TemporaryDirectory() as td:
    memory=CounterfactualDecisionMemory(os.path.join(td,"cf.sqlite3"))
    for i in range(3):
        p={"decision":"AUTO_ALLOW","risk":"LOW","plan_hash":f"SMOKE-{i}","side_effects":"NONE","actions":[]}
        r=memory.record_prediction(project_id="SMOKE", requested_by="operator", prediction=p)
        memory.observe_outcome(prediction_id=r["prediction_id"], actual={"decision":"REVIEW","risk":"HIGH"})
    out=AdaptiveDecisionIntelligence(memory).advise_for_project("SMOKE", candidate_decision="AUTO_ALLOW", candidate_risk="LOW")
    print(out)
    assert out["advisory_posture"] == "ELEVATED_CAUTION"
    assert out["governance_authority"] == "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE"
    memory.close()
