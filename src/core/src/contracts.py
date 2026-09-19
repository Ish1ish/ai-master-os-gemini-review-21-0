from typing import Dict, Any, List


REQUIRED_RUNTIME_STAGES = [
    "market","ideas","strategy","product","brand","content",
    "visual","marketing","sales","automation","analytics"
]

EXPECTED_ENGINE_IDS = {
    "market":"E-02",
    "ideas":"E-03",
    "strategy":"E-04",
    "product":"E-05",
    "brand":"E-06",
    "content":"E-07",
    "visual":"E-08",
    "marketing":"E-09",
    "sales":"E-10",
    "automation":"E-11",
    "analytics":"E-12",
}


def check_stage_contracts(result: Dict[str, Any]) -> Dict[str, Any]:
    missing=[s for s in REQUIRED_RUNTIME_STAGES if s not in result]
    wrong=[]
    for s in REQUIRED_RUNTIME_STAGES:
        if s in result and isinstance(result[s],dict):
            actual=result[s].get("engine_id")
            if actual != EXPECTED_ENGINE_IDS[s]:
                wrong.append({"stage":s,"expected":EXPECTED_ENGINE_IDS[s],"actual":actual})
    return {
        "status":"PASS" if not missing and not wrong else "FAIL",
        "missing_stages":missing,
        "wrong_engine_ids":wrong,
    }
