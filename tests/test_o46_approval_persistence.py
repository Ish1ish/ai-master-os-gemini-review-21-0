import json
from pathlib import Path
from tempfile import TemporaryDirectory

from core.src.human_approval_boundary import ApprovalState
from core.src.human_approval_boundary_integration import GovernedAutonomousApprovalIntegration
from core.src.multi_dimensional_resource_governor import ResourceLimits
from core.src.persistent_human_approval import ApprovalCheckpointStore, PersistentHumanApprovalIntegration
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
        limits=ResourceLimits(max_time_ms=5000, max_provider_calls=8, max_retry_attempts=2, max_concurrency=1, max_cycles=2),
    )
    return GovernedAutonomousApprovalIntegration(loop=loop)


def main():
    with TemporaryDirectory() as td:
        checkpoint_path = Path(td) / 'approval_checkpoint.json'
        store = ApprovalCheckpointStore(checkpoint_path)
        first = PersistentHumanApprovalIntegration(checkpoint_store=store, integration=build_integration())
        pending_1 = first.run_to_approval(topic='S63 persistence test')
        first_trace_ids = pending_1.cycle_trace_ids

        # Simulate process restart: a brand-new integration instance rehydrates the same checkpoint.
        restarted = PersistentHumanApprovalIntegration(checkpoint_store=ApprovalCheckpointStore(checkpoint_path), integration=build_integration())
        pending_2 = restarted.run_to_approval(topic='THIS MUST NOT RE-RUN')

        approved = restarted.approve(pending_2.action_id, 'human-resume')
        approved_again = restarted.approve(pending_2.action_id, 'human-resume')
        snapshot = restarted.checkpoint_snapshot()

        checks = [
            pending_1.status == 'AWAITING_APPROVAL',
            pending_1.request_state == ApprovalState.AWAITING_APPROVAL.value,
            checkpoint_path.exists(),
            pending_2.action_id == pending_1.action_id,
            pending_2.request_fingerprint == pending_1.request_fingerprint,
            pending_2.cycle_trace_ids == first_trace_ids,
            approved.state == ApprovalState.APPROVED,
            approved.released is True,
            approved.external_action_executed is False,
            approved_again == approved,
            snapshot['decision_state'] == ApprovalState.APPROVED.value,
            tuple(snapshot['cycle_trace_ids']) == first_trace_ids,
            restarted.integration.approval_boundary.can_release_external(pending_2.action_id) is True,
            snapshot['released'] is True,
            restarted.integration.approval_boundary.snapshot()['external_action_executed'] is False,
            len(first_trace_ids) == 2,
            first_trace_ids[0] != first_trace_ids[1],
            'external_action_executed' not in snapshot or snapshot.get('external_action_executed') is False,
        ]
        assert len(checks) == 18 and all(checks), [i for i, value in enumerate(checks, 1) if not value]
        print('S63_TARGETED_TESTS_PASS 18/18')


if __name__ == '__main__':
    main()
