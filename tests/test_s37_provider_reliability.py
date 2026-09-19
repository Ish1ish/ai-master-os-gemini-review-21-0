import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from core.src.provider_resilience import (  # noqa: E402
    ProviderCircuitOpenError,
    ProviderReliabilityConfig,
    ProviderRequestError,
    call_with_provider_reliability,
    reset_provider_reliability_state,
)


def test_transient_503_retries_then_succeeds():
    reset_provider_reliability_state()
    calls = []
    failures = iter([503, None])

    def op():
        calls.append(1)
        code = next(failures)
        if code:
            raise ProviderRequestError("temporary", status_code=code)
        return "OK"

    cfg = ProviderReliabilityConfig(max_attempts=3, backoff_s=0, max_backoff_s=0)
    assert call_with_provider_reliability("model", op, cfg) == "OK"
    assert len(calls) == 2


def test_rate_limit_uses_bounded_retry():
    reset_provider_reliability_state()
    calls = []

    def op():
        calls.append(1)
        raise ProviderRequestError("rate", status_code=429, retry_after=0)

    cfg = ProviderReliabilityConfig(max_attempts=3, backoff_s=0, max_backoff_s=0)
    try:
        call_with_provider_reliability("search", op, cfg)
    except ProviderRequestError:
        pass
    else:
        raise AssertionError("expected provider request failure")
    assert len(calls) == 3


def test_non_retryable_4xx_fails_without_retry():
    reset_provider_reliability_state()
    calls = []

    def op():
        calls.append(1)
        raise ProviderRequestError("bad request", status_code=400)

    cfg = ProviderReliabilityConfig(max_attempts=5, backoff_s=0, max_backoff_s=0)
    try:
        call_with_provider_reliability("model", op, cfg)
    except ProviderRequestError:
        pass
    else:
        raise AssertionError("expected provider request failure")
    assert len(calls) == 1


def test_circuit_opens_after_repeated_terminal_transient_failures():
    reset_provider_reliability_state()

    def op():
        raise ProviderRequestError("down", status_code=503)

    cfg = ProviderReliabilityConfig(
        max_attempts=1,
        backoff_s=0,
        max_backoff_s=0,
        circuit_failure_threshold=2,
        circuit_cooldown_s=60,
    )
    for _ in range(2):
        try:
            call_with_provider_reliability("model", op, cfg)
        except ProviderRequestError:
            pass
    try:
        call_with_provider_reliability("model", op, cfg)
    except ProviderCircuitOpenError:
        return
    raise AssertionError("circuit should be open")


def test_half_open_probe_can_recover_after_cooldown():
    reset_provider_reliability_state()
    outcomes = [ProviderRequestError("down", status_code=503), "RECOVERED"]
    cfg = ProviderReliabilityConfig(
        max_attempts=1,
        backoff_s=0,
        max_backoff_s=0,
        circuit_failure_threshold=1,
        circuit_cooldown_s=0,
    )

    def op():
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    try:
        call_with_provider_reliability("search", op, cfg)
    except ProviderRequestError:
        pass
    assert call_with_provider_reliability("search", op, cfg) == "RECOVERED"


def run_all_tests():
    tests = [
        test_transient_503_retries_then_succeeds,
        test_rate_limit_uses_bounded_retry,
        test_non_retryable_4xx_fails_without_retry,
        test_circuit_opens_after_repeated_terminal_transient_failures,
        test_half_open_probe_can_recover_after_cooldown,
    ]
    for test in tests:
        test()
    return len(tests)


if __name__ == "__main__":
    count = run_all_tests()
    print(f"S37_TARGETED_TESTS_PASS {count}/{count}")
