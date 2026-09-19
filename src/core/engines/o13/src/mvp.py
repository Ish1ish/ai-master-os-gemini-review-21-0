class MVPPlanner:
    def build(self, idea, model_option, constraints=None):
        constraints=list(constraints or [])
        return {
            "mvp_goal":"Prove the highest-risk assumption with the smallest useful version.",
            "business_model":model_option.get("name"),
            "scope":[
                "One clearly defined target segment",
                "One core problem",
                "One core promise/outcome",
                "One primary acquisition path",
                "One conversion path",
                "Manual or lightweight delivery where practical",
            ],
            "exclude_for_now":[
                "Large feature sets",
                "Complex automation before process validation",
                "Multiple acquisition channels simultaneously",
                "Brand complexity that does not improve validation",
            ],
            "validation_metrics":["Qualified interest","Activation / completion","Conversion or paid pilot","Customer feedback","Contribution economics"],
            "constraints":constraints,
        }
