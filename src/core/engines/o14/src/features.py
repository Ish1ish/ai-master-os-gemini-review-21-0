class FeaturePrioritizer:
    def prioritize(self, modules, strategy):
        features=[]
        for module in modules:
            must=module.get("priority")=="MUST"
            features.append({
                "feature_id":module["module_id"],
                "name":module["name"],
                "user_value":module["purpose"],
                "priority":module.get("priority","SHOULD"),
                "estimated_effort":"LOW" if must else "MEDIUM",
                "decision_rule":"Keep when it directly supports the core promise or validation." if must else "Add only after the core workflow works and evidence justifies it.",
            })
        return {
            "features":features,
            "prioritization_rule":"Value to core outcome first, then validation impact, then effort.",
        }
