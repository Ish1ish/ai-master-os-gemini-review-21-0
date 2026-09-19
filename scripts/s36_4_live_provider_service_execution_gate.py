import hashlib
import json
import os
import tempfile
import traceback
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _compact_result(result):
    if not isinstance(result, dict):
        return {"type": type(result).__name__}
    keep = {}
    for key in (
        "status", "run_id", "failed_stage", "error", "runtime_status",
        "handoff_qa", "handoff_chain_qa", "provider", "model",
    ):
        if key in result:
            value = result[key]
            if isinstance(value, (dict, list)):
                keep[key] = value
            else:
                keep[key] = value
    runtime_result = result.get("runtime_result")
    if isinstance(runtime_result, dict):
        keep["runtime_result"] = {
            k: runtime_result.get(k)
            for k in ("status", "failed_stage", "provider", "model", "error")
            if k in runtime_result
        }
    return keep


def _provider_evidence(obj):
    seen = set()
    hits = []

    def walk(x, path, depth=0):
        if depth > 8 or len(hits) >= 24:
            return
        oid = id(x)
        if oid in seen:
            return
        seen.add(oid)

        if isinstance(x, dict):
            for k, v in x.items():
                lk = str(k).lower()
                if lk in {"provider", "model", "text", "results", "raw_output_hash", "latency_ms"}:
                    hits.append({"path": f"{path}.{k}", "value_type": type(v).__name__})
                if isinstance(v, (dict, list, tuple)):
                    walk(v, f"{path}.{k}", depth + 1)
        elif isinstance(x, (list, tuple)):
            for i, v in enumerate(x[:12]):
                if isinstance(v, (dict, list, tuple)):
                    walk(v, f"{path}[{i}]", depth + 1)
        elif hasattr(x, "__dict__"):
            for k, v in vars(x).items():
                if str(k).startswith("_"):
                    continue
                if isinstance(v, (dict, list, tuple)) or hasattr(v, "__dict__"):
                    walk(v, f"{path}.{k}", depth + 1)

    walk(obj, "result")
    return hits


def main() -> int:
    # The caller must already have configured the real provider credentials.
    # This gate never prints credential values.
    os.environ["AI_OS_ENV"] = "production"
    os.environ.pop("AI_OS_MEMORY_DB_PATH", None)
    os.environ.pop("AI_OS_AUDIT_DB_PATH", None)

    repo = Path(__file__).resolve().parents[1]
    service_path = repo / "src" / "core" / "src" / "service.py"

    output_path = repo / "staging" / "s36_4_live_provider_service_execution.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "release": "O39-S36.4",
        "status": "FAIL",
        "service_module": "core.src.service",
        "runtime_module": "core.src.real_wiring",
        "provider_module": "core.src.live_providers",
        "checks": {
            "service_source_hash": _sha256(service_path) if service_path.exists() else None,
            "provider_configuration": None,
            "service_constructed": False,
            "submit_status": None,
            "execute_status": None,
            "run_completed": False,
            "provider_evidence_present": False,
            "external_action_executed": False,
            "memory_write_executed": False,
        },
        "result": {},
        "notes": [],
    }

    try:
        from core.src.live_providers import provider_configuration_status
        cfg = provider_configuration_status()
        safe_cfg = {
            "status": cfg.get("status"),
            "model_configured": bool(cfg.get("model_configured")),
            "search_configured": bool(cfg.get("search_configured")),
            "missing": list(cfg.get("missing", [])),
        }
        report["checks"]["provider_configuration"] = safe_cfg

        if cfg.get("status") != "CONFIGURED":
            report["notes"].append("real_provider_configuration_incomplete")
            output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print("S36_4_REAL_PROVIDER_SERVICE_NOT_CONFIGURED")
            return 1

        from core.src.service import ApplicationService

        with tempfile.TemporaryDirectory(prefix="aios_s36_4_") as td:
            db_path = str(Path(td) / "jobs.sqlite3")
            service = ApplicationService(db_path=db_path)
            report["checks"]["service_constructed"] = True

            submit = service.submit(
                project_id="S36-4-STAGING",
                request=(
                    "Perform a controlled staging evaluation of a hypothetical small-business "
                    "AI workflow. Use live research and a live model. Keep the reasoning concise, "
                    "avoid consequential actions, and produce a structured internal result."
                ),
                audience="small businesses evaluating AI workflow automation",
                goal="controlled live-provider staging validation",
                constraints=[
                    "staging-only",
                    "no external consequential action",
                    "no autonomous publishing",
                    "no spending",
                    "no messaging",
                    "no memory persistence requirement",
                ],
                language="en",
                internal=True,
            )
            report["checks"]["submit_status"] = submit.get("status")
            job_id = submit.get("job_id")
            if not job_id:
                report["notes"].append("submit_did_not_create_job")
            else:
                result = service.execute(job_id, internal=True)
                report["checks"]["execute_status"] = result.get("status")
                report["result"] = _compact_result(result)
                report["checks"]["provider_evidence_present"] = bool(_provider_evidence(result))
                report["checks"]["run_completed"] = result.get("status") == "COMPLETE"

                runtime_result = result.get("result") if isinstance(result, dict) else None
                if isinstance(runtime_result, dict):
                    report["checks"]["external_action_executed"] = bool(
                        runtime_result.get("external_action_executed", False)
                    )
                    report["checks"]["memory_write_executed"] = bool(
                        runtime_result.get("memory_write_executed", False)
                    )
                else:
                    report["checks"]["external_action_executed"] = bool(
                        result.get("external_action_executed", False)
                    )
                    report["checks"]["memory_write_executed"] = bool(
                        result.get("memory_write_executed", False)
                    )

                if not report["checks"]["run_completed"]:
                    report["notes"].append(
                        "service_runtime_execution_failed"
                    )
            service.close()

        strict = (
            report["checks"]["provider_configuration"]["status"] == "CONFIGURED"
            and report["checks"]["service_constructed"]
            and report["checks"]["submit_status"] == "QUEUED"
            and report["checks"]["execute_status"] == "COMPLETE"
            and report["checks"]["run_completed"]
            and report["checks"]["provider_evidence_present"]
            and not report["checks"]["external_action_executed"]
            and not report["checks"]["memory_write_executed"]
        )
        report["status"] = "PASS" if strict else "FAIL"

    except Exception as exc:
        report["notes"].append("gate_exception")
        report["result"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback_tail": traceback.format_exc().splitlines()[-8:],
        }

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if report["status"] == "PASS":
        print("S36_4_LIVE_PROVIDER_SERVICE_EXECUTION_PASS")
        return 0

    print("S36_4_LIVE_PROVIDER_SERVICE_EXECUTION_FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
