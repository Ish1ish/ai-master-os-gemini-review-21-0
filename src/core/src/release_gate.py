
class UnifiedReleaseGate:
    def evaluate(self, o29_status, o31_health, o34_smoke, o25_security):
        issues=[]
        if o29_status!="RELEASE_CANDIDATE":
            issues.append({"type":"o29_gate_blocked","status":o29_status})
        if o31_health!="HEALTHY":
            issues.append({"type":"o31_health_unhealthy","status":o31_health})
        if o34_smoke!="PASS":
            issues.append({"type":"o34_smoke_failed","status":o34_smoke})
        if o25_security!="PASS":
            issues.append({"type":"o25_security_failed","status":o25_security})
        return {"status":"PASS" if not issues else "BLOCKED","issues":issues}
