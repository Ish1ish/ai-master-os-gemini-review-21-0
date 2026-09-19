from core.src.human_approval_boundary import (
    ActionRisk,
    ApprovalState,
    HumanApprovalBoundary,
)


def main():
    gate = HumanApprovalBoundary()

    bounded = gate.request(
        action_id="S61-BOUNDED-001",
        action_type="provider_synthesis",
        risk=ActionRisk.BOUNDED,
        summary="Prepare a bounded internal synthesis",
    )
    bounded_release = gate.release_bounded(bounded.action_id)

    consequential = gate.request(
        action_id="S61-CONSEQUENTIAL-001",
        action_type="external_publish",
        risk=ActionRisk.CONSEQUENTIAL,
        summary="Publish an externally visible result",
    )
    preapproval = gate.snapshot()
    attempted_auto = gate.can_release_external(consequential.action_id)
    missing_identity = gate.approve(action_id=consequential.action_id, approver_id=" ")
    rejected = gate.reject(
        action_id=consequential.action_id,
        approver_id="human-1",
        reason="manual rejection for boundary test",
    )

    # Recreate a separate consequential request to prove explicit approval.
    approved_request = gate.request(
        action_id="S61-CONSEQUENTIAL-002",
        action_type="external_message",
        risk=ActionRisk.CONSEQUENTIAL,
        summary="Send an externally visible message",
    )
    approved = gate.approve(action_id=approved_request.action_id, approver_id="human-1")
    approved_again = gate.approve(action_id=approved_request.action_id, approver_id="human-1")

    checks = [
        bounded.state == ApprovalState.NOT_REQUIRED,
        bounded_release.released,
        bounded_release.external_action_executed is False,
        consequential.state == ApprovalState.AWAITING_APPROVAL,
        preapproval["request_count"] == 2,
        attempted_auto is False,
        missing_identity.state == ApprovalState.AWAITING_APPROVAL,
        rejected.state == ApprovalState.REJECTED,
        rejected.released is False,
        approved.state == ApprovalState.APPROVED,
        approved.released is True,
        approved.external_action_executed is False,
        approved.auto_approved is False,
        approved_again.decision_fingerprint == approved.decision_fingerprint,
        gate.can_release_external(approved_request.action_id) is True,
    ]
    assert len(checks) == 15 and all(checks), [i for i, value in enumerate(checks, 1) if not value]
    print("S61_TARGETED_TESTS_PASS 15/15")


if __name__ == "__main__":
    main()
