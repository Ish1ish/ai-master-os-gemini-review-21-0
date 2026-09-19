class ProductArchitectureBuilder:
    def build(self, product_definition, strategy):
        model=product_definition.get("product_type","Unspecified")
        if model=="Service / Productized Service":
            delivery="Service workflow + reusable templates/checklists + client-facing outcome"
            fmt="Manual or lightweight assisted delivery"
        elif model=="Digital Product":
            delivery="Self-contained digital product with structured modules/assets"
            fmt="Digital files / guided product experience"
        else:
            delivery="Service-led validation plus reusable productized components"
            fmt="Hybrid"
        modules=[
            {"module_id":"MOD-01","name":"Core Outcome","purpose":"Deliver the single primary customer outcome.","priority":"MUST"},
            {"module_id":"MOD-02","name":"Onboarding / Setup","purpose":"Get the customer to a first useful result quickly.","priority":"MUST"},
            {"module_id":"MOD-03","name":"Guidance / Support","purpose":"Reduce friction and help the customer succeed.","priority":"SHOULD"},
            {"module_id":"MOD-04","name":"Proof / Examples","purpose":"Show how the product should be used and what good output looks like.","priority":"SHOULD"},
        ]
        return {
            "delivery_model":delivery,
            "format":fmt,
            "modules":modules,
            "architecture_principle":"Build the minimum coherent product needed to deliver the promise; defer features that do not improve validation or the core outcome.",
        }
