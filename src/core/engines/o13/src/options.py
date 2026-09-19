from typing import Dict, Any, List

class BusinessModelBuilder:
    def build_options(self, idea: Dict[str, Any], constraints: List[str] | None = None) -> List[Dict[str, Any]]:
        constraints = list(constraints or [])
        base = (idea.get("idea") or idea.get("evidence_summary") or "").strip()
        return [
            {"model_id":"BM-01","name":"Digital Product",
             "description":f"Package the core solution as a digital product: {base}",
             "fit":"repeatable delivery and low marginal cost",
             "risks":["build_before_validation","weak_distribution"]},
            {"model_id":"BM-02","name":"Service / Productized Service",
             "description":f"Deliver the solution as a focused service first: {base}",
             "fit":"fast learning and manual validation",
             "risks":["time_bound_delivery","lower_scalability"]},
            {"model_id":"BM-03","name":"Hybrid Product + Service",
             "description":f"Use service delivery to validate and productize the repeatable core: {base}",
             "fit":"problem is clear but product scope is uncertain",
             "risks":["operational_complexity","premature_productization"]},
        ]
