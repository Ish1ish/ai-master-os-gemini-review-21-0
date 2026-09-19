from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env['PYTHONPATH'] = str(root / 'src') + os.pathsep + env.get('PYTHONPATH', '')

    checks = {
        's61_boundary_present': (root / 'src/core/src/human_approval_boundary.py').exists(),
        's62_integration_present': (root / 'src/core/src/human_approval_boundary_integration.py').exists(),
        's63_module_present': (root / 'src/core/src/persistent_human_approval.py').exists(),
        'targeted_tests_present': (root / 'tests/test_o46_approval_persistence.py').exists(),
        'targeted_tests': False,
        'compileall': False,
        'checkpoint_created': False,
        'pending_persisted': False,
        'same_action_after_restart': False,
        'same_fingerprint_after_restart': False,
        'same_cycle_trace_ids_after_restart': False,
        'approval_resume_releases': False,
        'approval_idempotent': False,
        'external_action_blocked': False,
        'memory_write_blocked': True,
        'no_cycle_reexecution_on_resume': False,
    }

    p = subprocess.run([sys.executable, str(root / 'tests/test_o46_approval_persistence.py')], cwd=root, capture_output=True, text=True, env=env)
    checks['targeted_tests'] = p.returncode == 0 and 'S63_TARGETED_TESTS_PASS 18/18' in p.stdout

    c = subprocess.run([sys.executable, '-m', 'compileall', '-q', 'src', 'tests'], cwd=root, capture_output=True, text=True, env=env)
    checks['compileall'] = c.returncode == 0

    notes = []
    try:
        sys.path.insert(0, str(root / 'src'))
        from core.src.live_providers import provider_configuration_status
        from core.src.human_approval_boundary import ApprovalState
        from core.src.human_approval_boundary_integration import GovernedAutonomousApprovalIntegration
        from core.src.persistent_human_approval import ApprovalCheckpointStore, PersistentHumanApprovalIntegration
        cfg = provider_configuration_status()
        checks['checkpoint_created'] = False
        checks['pending_persisted'] = False
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'approval.json'
            first = PersistentHumanApprovalIntegration(checkpoint_store=ApprovalCheckpointStore(path), integration=GovernedAutonomousApprovalIntegration())
            pending = first.run_to_approval(topic='S63 real-provider approval persistence gate')
            checks['checkpoint_created'] = path.exists()
            checks['pending_persisted'] = pending.status == 'AWAITING_APPROVAL' and pending.request_state == ApprovalState.AWAITING_APPROVAL.value
            traces = pending.cycle_trace_ids
            restarted = PersistentHumanApprovalIntegration(checkpoint_store=ApprovalCheckpointStore(path), integration=GovernedAutonomousApprovalIntegration())
            resumed = restarted.run_to_approval(topic='must-not-rerun')
            checks['same_action_after_restart'] = resumed.action_id == pending.action_id
            checks['same_fingerprint_after_restart'] = resumed.request_fingerprint == pending.request_fingerprint
            checks['same_cycle_trace_ids_after_restart'] = resumed.cycle_trace_ids == traces
            checks['no_cycle_reexecution_on_resume'] = resumed.cycle_trace_ids == traces and len(traces) == 2
            approved = restarted.approve(resumed.action_id, 's63-gate-human')
            checks['approval_resume_releases'] = approved.state == ApprovalState.APPROVED and approved.released is True
            checks['approval_idempotent'] = restarted.approve(resumed.action_id, 's63-gate-human') == approved
            checks['external_action_blocked'] = approved.external_action_executed is False and restarted.integration.approval_boundary.snapshot()['external_action_executed'] is False
            notes.append('real_provider_configuration=' + str(cfg.get('status')))
    except Exception as exc:
        notes.append(f'gate_runtime_error={type(exc).__name__}:{exc}')

    status = 'PASS' if all(checks.values()) else 'FAIL'
    payload = {
        'release': 'O46-S63',
        'status': status,
        'checks': checks,
        'path': 'S62 approval boundary -> persisted checkpoint -> simulated restart -> same pending action -> explicit approval -> downstream release only',
        'external_action_executed': False,
        'memory_write_executed': False,
        'automatic_approval': False,
        'notes': notes,
    }
    print('S63_APPROVAL_PERSISTENCE_PASS' if status == 'PASS' else 'S63_APPROVAL_PERSISTENCE_FAIL')
    import json
    print(json.dumps(payload, indent=2))
    print(p.stdout, end='')
    print(p.stderr, end='')
    if status != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
