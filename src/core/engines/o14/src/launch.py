class LaunchReadiness:
    def build(self, product_definition, architecture, features):
        checks=[
            {"check_id":"LR-01","check":"Core promise is clear","required":True,"status":"READY" if product_definition.get("core_promise") else "BLOCKED"},
            {"check_id":"LR-02","check":"Primary audience is defined","required":True,"status":"READY" if product_definition.get("target_audience") else "BLOCKED"},
            {"check_id":"LR-03","check":"MVP modules are defined","required":True,"status":"READY" if architecture.get("modules") else "BLOCKED"},
            {"check_id":"LR-04","check":"MUST features are separated from later features","required":True,"status":"READY" if any(x.get("priority")=="MUST" for x in features.get("features",[])) else "BLOCKED"},
            {"check_id":"LR-05","check":"Customer delivery path is defined","required":True,"status":"READY" if product_definition.get("product_type") else "BLOCKED"},
            {"check_id":"LR-06","check":"Validation gate exists before full build","required":True,"status":"READY"},
        ]
        return {
            "status":"READY" if all(x["status"]=="READY" for x in checks if x["required"]) else "BLOCKED",
            "checks":checks,
            "gate":"Validate the core customer outcome with real users before expanding scope.",
        }
