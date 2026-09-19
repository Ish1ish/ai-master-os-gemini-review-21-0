from core.src.o46_governed_autonomous_loop import GovernedAutonomousLoopPrototype


def main() -> None:
    loop = GovernedAutonomousLoopPrototype()
    result = loop.run(project_id="O46-TEST", topic="bounded prototype")
    assert result.status == "PASS"
    assert result.closed_loop
    assert result.reentered
    assert len(result.cycles) == 2
    assert result.cycles[0].outcome_status == "SUCCESS"
    assert result.cycles[1].decision.decision_id == "O46-D2"
    assert result.cycles[1].next_decision == "STOP_OR_REQUEST_APPROVAL"
    assert result.cycles[0].trace_id != result.cycles[1].trace_id
    assert result.external_action_executed is False
    assert result.memory_write_executed is False
    assert result.execution_triggered is False

    blocked = GovernedAutonomousLoopPrototype(
        limits=__import__("core.src.multi_dimensional_resource_governor", fromlist=["ResourceLimits"]).ResourceLimits(
            max_time_ms=1, max_provider_calls=1, max_retry_attempts=1, max_concurrency=1, max_cycles=1
        )
    ).run(project_id="O46-BUDGET")
    assert blocked.status == "FAIL_CLOSED"
    print("S59_TARGETED_TESTS_PASS 12/12")


if __name__ == "__main__":
    main()
