def build_risk_map(idea, constraints=None):
    constraints=list(constraints or [])
    risks=[
        {"risk_id":"R-01","risk":"Demand Risk","question":"Will enough target customers care enough to act or pay?","severity":"HIGH","mitigation":"Customer interviews, landing-page test, preorders, paid pilot."},
        {"risk_id":"R-02","risk":"Distribution Risk","question":"Can the audience be reached economically?","severity":"HIGH","mitigation":"Test one primary acquisition channel before scaling."},
        {"risk_id":"R-03","risk":"Competitive Risk","question":"Can alternatives solve the same problem better or cheaper?","severity":"MEDIUM","mitigation":"Current competitor mapping and explicit differentiation."},
        {"risk_id":"R-04","risk":"Execution Risk","question":"Can the MVP be delivered within current resources?","severity":"MEDIUM","mitigation":"Narrow scope and choose the simplest delivery model."},
        {"risk_id":"R-05","risk":"Economic Risk","question":"Can revenue exceed acquisition and delivery costs?","severity":"HIGH","mitigation":"Test price, margin, AOV, and acquisition economics before scaling."},
    ]
    if any("low" in c.lower() and "cost" in c.lower() for c in constraints):
        risks.append({"risk_id":"R-06","risk":"Constraint Fit Risk","question":"Does the plan exceed the user's low-cost constraint?","severity":"HIGH","mitigation":"Prefer manual/service-first validation and low-cost MVP experiments."})
    return {"idea":idea.get("idea",""),"risks":risks}
