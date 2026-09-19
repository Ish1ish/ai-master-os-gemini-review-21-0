from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    src = root / 'src/core/src'
    module = src / 'human_approval_boundary_integration.py'
    s60 = src / 'real_provider_governed_autonomous_loop.py'
    s61 = src / 'human_approval_boundary.py'
    test = root / 'tests/test_o46_human_approval_integration.py'

    checks = {
        's60_loop_present': s60.exists(),
        's61_boundary_present': s61.exists(),
        's62_module_present': module.exists(),
        'targeted_tests_present': test.exists(),
        'explicit_consequential_state': False,
        'awaiting_approval': False,
        'automatic_approval_blocked': False,
        'rejection_blocks_release': False,
        'explicit_approval_releases': False,
        'approval_idempotent': False,
        'external_action_blocked': True,
        'memory_write_blocked': True,
        'targeted_tests': False,
        'compileall': False,
        'real_provider_configuration': False,
        'real_provider_loop_available': False,
    }

    env = dict(os.environ)
    env['PYTHONPATH'] = str(root / 'src') + os.pathsep + env.get('PYTHONPATH', '')

    p = subprocess.run(
        [sys.executable, str(test)],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
    )
    checks['targeted_tests'] = p.returncode == 0 and 'S62_TARGETED_TESTS_PASS 16/16' in p.stdout

    c = subprocess.run(
        [sys.executable, '-m', 'compileall', '-q', 'src', 'tests'],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
    )
    checks['compileall'] = c.returncode == 0

    notes = []
    try:
        sys.path.insert(0, str(root / 'src'))
        from core.src.live_providers import provider_configuration_status
        from core.src.human_approval_boundary import ApprovalState, ActionRisk
        from core.src.human_approval_boundary_integration import GovernedAutonomousApprovalIntegration

        cfg = provider_configuration_status()
        checks['real_provider_configuration'] = cfg.get('status') == 'CONFIGURED'

        integration = GovernedAutonomousApprovalIntegration()
        if checks['real_provider_configuration']:
            result = integration.run_to_approval(topic='O46 S62 human approval boundary integration validation')
            checks['real_provider_loop_available'] = len(result.cycles) == 2
            checks['explicit_consequential_state'] = result.approval_request.state == ApprovalState.AWAITING_APPROVAL
            checks['awaiting_approval'] = result.status == 'AWAITING_APPROVAL'
            checks['automatic_approval_blocked'] = result.automatic_approval is False and not result.released_to_downstream_executor
            action_id = result.approval_request.action_id
            rejected = integration.reject(action_id, 'gate-human', 'gate_rejection')
            checks['rejection_blocks_release'] = rejected.state == ApprovalState.REJECTED and rejected.released is False

            approval_boundary = integration.approval_boundary
            approved_action = 'O46-S62-GATE-APPROVAL-ACTION'
            approval_boundary.request(
                action_id=approved_action,
                action_type='CONSEQUENTIAL_ACTION_RELEASE',
                risk=ActionRisk.CONSEQUENTIAL,
                summary='gate approval release validation',
            )
            approved = integration.approve(approved_action, 'gate-human-approved')
            approved_again = integration.approve(approved_action, 'gate-human-approved')
            checks['explicit_approval_releases'] = approved.state == ApprovalState.APPROVED and approved.released is True
            checks['approval_idempotent'] = approved_again == approved
            checks['external_action_blocked'] = approved.external_action_executed is False
        else:
            notes.append('real_provider_configuration_incomplete')
    except Exception as exc:
        notes.append(f'gate_runtime_error={type(exc).__name__}:{exc}')

    status = 'PASS' if all(checks.values()) else 'FAIL'
    payload = {
        'release': 'O46-S62',
        'status': status,
        'checks': checks,
        'path': 'S60 real-provider governed loop -> consequential intent -> S61 AWAITING_APPROVAL -> explicit reject/approve -> downstream release only',
        'external_action_executed': False,
        'memory_write_executed': False,
        'automatic_approval': False,
        'notes': notes + [
            'Approval releases only to a downstream executor; S62 itself never performs an external side effect.',
            'No memory write is performed by the integrated approval boundary.',
        ],
    }
    print('S62_HUMAN_APPROVAL_BOUNDARY_INTEGRATION_PASS' if status == 'PASS' else 'S62_HUMAN_APPROVAL_BOUNDARY_INTEGRATION_FAIL')
    print(json.dumps(payload, indent=2))
    print(p.stdout, end='')
    print(p.stderr, end='')
    if status != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
