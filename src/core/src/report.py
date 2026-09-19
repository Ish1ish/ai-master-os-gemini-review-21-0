import json


def write_report(path, report):
    with open(path,"w",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)


def release_gate(report):
    summary=report["summary"]
    return {
        "status":"RELEASE_CANDIDATE" if summary["release_status"]=="PASS" else "BLOCKED",
        "reason":(
            "All required evaluation checks passed."
            if summary["release_status"]=="PASS"
            else "At least one required evaluation check failed or errored."
        ),
    }
