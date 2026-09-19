import json

from core.src.human_approval_boundary_integration import GovernedAutonomousApprovalIntegration
from core.src.human_approval_boundary import ApprovalState
from core.src.multi_dimensional_resource_governor import ResourceLimits
from core.src.real_provider_governed_autonomous_loop import RealProviderGovernedAutonomousLoop


def model_stub(prompt):
    payload = json.loads(prompt)
    if payload['task'].startswith('Return JSON only with fields decision'):
        return {'text': json.dumps({'decision': 'PROCEED_WITH_BOUNDED_VALIDATION', 'rationale': 'stub'})}
    return {'text': json.dumps({'status': 'SUCCESS', 'result': 'bounded'})}


def search_stub(query):
    return {'results': [{'title': 'stub evidence', 'url': 'stub://evidence-1', 'snippet': 'evidence'}]}


def build_integration():
    loop = RealProviderGovernedAutonomousLoop(
        model_fn=model_stub,
        search_fn=search_stub,
        limits=ResourceLimits(
            max_time_ms=5000,
            max_provider_calls=8,
            max_retry_attempts=2,
            max_concurrency=1,
            max_cycles=2,
        ),
    )
    return GovernedAutonomousApprovalIntegration(loop=loop)


def main():
    integration = build_integration()
    result = integration.run_to_approval()
    action_id = result.approval_request.action_id

    rejected = integration.reject(action_id, 'human-001', 'not_ready')

    fresh = build_integration()
    pending = fresh.run_to_approval()
    pending_action = pending.approval_request.action_id
    approved = fresh.approve(pending_action, 'human-003')
    approved_again = fresh.approve(pending_action, 'human-003')

    checks = [
        result.status == 'AWAITING_APPROVAL',
        result.approval_request.state == ApprovalState.AWAITING_APPROVAL,
        result.automatic_approval is False,
        result.released_to_downstream_executor is False,
        result.external_action_executed is False,
        result.memory_write_executed is False,
        len(result.cycles) == 2,
        rejected.state == ApprovalState.REJECTED,
        rejected.released is False,
        rejected.external_action_executed is False,
        rejected.auto_approved is False,
        approved.external_action_executed is False,
        approved.state == ApprovalState.APPROVED,
        approved_again == approved,
        fresh.can_release(pending_action) is True,
        fresh.approval_boundary.snapshot()['external_action_executed'] is False,
    ]
    assert len(checks) == 16 and all(checks), [i for i, value in enumerate(checks, 1) if not value]
    print('S62_TARGETED_TESTS_PASS 16/16')


if __name__ == '__main__':
    main()
