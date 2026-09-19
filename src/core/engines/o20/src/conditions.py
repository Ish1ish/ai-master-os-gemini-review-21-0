from typing import Dict, Any, List


class ConditionEngine:
    def evaluate(self, condition: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        field = condition.get("field")
        operator = condition.get("operator")
        expected = condition.get("value")

        actual = context.get(field)

        result = False
        supported = True

        if operator == "equals":
            result = actual == expected
        elif operator == "not_equals":
            result = actual != expected
        elif operator == "contains":
            result = expected in actual if isinstance(actual, (str, list, tuple, set)) else False
        elif operator == "greater_than":
            result = actual > expected
        elif operator == "less_than":
            result = actual < expected
        else:
            supported = False

        return {
            "status": "PASS" if supported else "FAIL",
            "matched": result if supported else False,
            "field": field,
            "operator": operator,
            "expected": expected,
            "actual": actual,
            "reason": "condition_evaluated" if supported else "unsupported_operator",
        }
