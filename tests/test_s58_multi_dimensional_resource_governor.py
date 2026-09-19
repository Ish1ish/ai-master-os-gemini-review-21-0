from core.src.multi_dimensional_resource_governor import MultiDimensionalResourceGovernor, ResourceLimits


def main() -> None:
    tests = []

    g = MultiDimensionalResourceGovernor(ResourceLimits(max_time_ms=1000, max_provider_calls=4, max_retry_attempts=3, max_concurrency=2, max_cycles=2))
    tests.append(g.admit(provider_calls=1, cycles=1).allowed)
    tests.append(g.usage.provider_calls == 1 and g.usage.cycles == 1)
    tests.append(g.admit(retry_attempts=1, concurrency=2).allowed)
    tests.append(g.peak_concurrency == 2)
    g.release_concurrency()
    tests.append(g.usage.concurrency == 1)
    tests.append(g.admit(time_ms=900).allowed)
    blocked_time = g.admit(time_ms=200)
    tests.append(not blocked_time.allowed and "time" in blocked_time.exhausted_dimensions)

    g2 = MultiDimensionalResourceGovernor(ResourceLimits(max_provider_calls=2))
    tests.append(g2.admit(provider_calls=2).allowed)
    blocked_calls = g2.admit(provider_calls=1)
    tests.append(not blocked_calls.allowed and "provider_calls" in blocked_calls.exhausted_dimensions)
    tests.append(g2.snapshot().status == "BLOCKED")

    g3 = MultiDimensionalResourceGovernor(ResourceLimits(max_cycles=1))
    tests.append(g3.admit(cycles=1).allowed)
    blocked_cycle = g3.admit(cycles=1)
    tests.append(not blocked_cycle.allowed and "cycles" in blocked_cycle.exhausted_dimensions)
    tests.append(g3.admit(provider_calls=1).status == "BLOCKED")

    g4 = MultiDimensionalResourceGovernor(ResourceLimits(max_retry_attempts=1))
    tests.append(g4.admit(retry_attempts=1).allowed)
    blocked_retry = g4.admit(retry_attempts=1)
    tests.append(not blocked_retry.allowed and "retry_attempts" in blocked_retry.exhausted_dimensions)

    assert len(tests) == 15
    assert all(tests), [i for i, value in enumerate(tests, 1) if not value]
    print("S58_TARGETED_TESTS_PASS 15/15")


if __name__ == "__main__":
    main()
