import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.src import live_providers  # noqa: E402
from core.src.provider_resilience import (  # noqa: E402
    ProviderCircuitOpenError,
    ProviderReliabilityConfig,
    ProviderRequestError,
    call_with_provider_reliability,
    reset_provider_reliability_state,
)


def _run_tests():
    import subprocess
    result = subprocess.run(
        [sys.executable, "tests/test_s37_provider_reliability.py"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def main():
    checks = {}

    checks["provider_resilience_imported"] = True
    checks["live_provider_imported"] = True
    checks["retry_config_defaults_bounded"] = ProviderReliabilityConfig().max_attempts == 3
    checks["live_provider_uses_reliability"] = "call_with_provider_reliability" in Path(live_providers.__file__).read_text(encoding="utf-8")

    reset_provider_reliability_state()
    calls = []
    sequence = iter([503, 503, None])

    def transient_op():
        calls.append(1)
        code = next(sequence)
        if code:
            raise ProviderRequestError("transient", status_code=code)
        return {"ok": True}

    cfg = ProviderReliabilityConfig(max_attempts=3, backoff_s=0, max_backoff_s=0)
    value = call_with_provider_reliability("gate-model", transient_op, cfg)
    checks["retries_transient_5xx"] = value == {"ok": True} and len(calls) == 3

    reset_provider_reliability_state()
    calls = []

    def rate_limited_op():
        calls.append(1)
        raise ProviderRequestError("rate", status_code=429, retry_after=0)

    try:
        call_with_provider_reliability("gate-search", rate_limited_op, cfg)
    except ProviderRequestError:
        rate_limit_failed_closed = True
    else:
        rate_limit_failed_closed = False
    checks["rate_limit_bounded"] = rate_limit_failed_closed and len(calls) == 3

    reset_provider_reliability_state()
    cfg_circuit = ProviderReliabilityConfig(max_attempts=1, backoff_s=0, max_backoff_s=0, circuit_failure_threshold=2, circuit_cooldown_s=60)

    def down_op():
        raise ProviderRequestError("down", status_code=503)

    for _ in range(2):
        try:
            call_with_provider_reliability("gate-circuit", down_op, cfg_circuit)
        except ProviderRequestError:
            pass
    try:
        call_with_provider_reliability("gate-circuit", down_op, cfg_circuit)
    except ProviderCircuitOpenError:
        circuit_opened = True
    else:
        circuit_opened = False
    checks["circuit_breaker_fail_closed"] = circuit_opened

    reset_provider_reliability_state()
    calls = []

    def permanent_bad_request():
        calls.append(1)
        raise ProviderRequestError("bad", status_code=400)

    cfg_more = ProviderReliabilityConfig(max_attempts=5, backoff_s=0, max_backoff_s=0)
    try:
        call_with_provider_reliability("gate-nonretryable", permanent_bad_request, cfg_more)
    except ProviderRequestError:
        nonretryable_fail_closed = True
    else:
        nonretryable_fail_closed = False
    checks["non_retryable_fails_without_retry"] = nonretryable_fail_closed and len(calls) == 1

    tests_ok, tests_output = _run_tests()
    checks["targeted_tests"] = tests_ok

    status = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "release": "O39-S37",
        "status": status,
        "checks": checks,
        "targeted_test_output": tests_output[-4000:],
        "external_action_executed": False,
        "memory_write_executed": False,
        "internet_facing_production_approval": False,
        "notes": [] if status == "PASS" else [k for k, v in checks.items() if not v],
    }
    out = ROOT / "staging" / "s37_provider_reliability.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("S37_PROVIDER_RELIABILITY_PASS" if status == "PASS" else "S37_PROVIDER_RELIABILITY_FAIL")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
