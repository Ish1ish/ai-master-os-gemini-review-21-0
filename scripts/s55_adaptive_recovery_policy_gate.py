from __future__ import annotations
import ast, json, subprocess, sys
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[1]
    src=root/'src/core/src/adaptive_recovery_policy.py'
    tests=root/'tests/test_s55_adaptive_recovery_policy.py'
    s54=root/'src/core/src/real_provider_failure_learning.py'
    checks={k:False for k in [
        's54_present','policy_engine_present','targeted_tests_present','policy_contract_present',
        'bounded_retry_present','fallback_present','fail_closed_present','policy_traceable',
        'deterministic_policy','idempotent_policy','execution_not_triggered','external_action_blocked',
        'memory_write_blocked','targeted_tests','compileall']}
    notes=[]; proc=None
    try:
        checks['s54_present']=s54.exists(); checks['policy_engine_present']=src.exists(); checks['targeted_tests_present']=tests.exists()
        text=src.read_text(encoding='utf-8') if src.exists() else ''
        if src.exists():
            tree=ast.parse(text); classes={n.name for n in tree.body if isinstance(n,ast.ClassDef)}
            checks['policy_contract_present']='RecoveryPolicy' in classes
            checks['bounded_retry_present']='BOUNDED_RETRY' in text and 'max_attempts' in text
            checks['fallback_present']='fallback' in text and 'FALLBACK_AND_REASSESS' in text
            checks['fail_closed_present']='FAIL_CLOSED' in text
            checks['policy_traceable']='evidence_refs' in text and 'learning_signal_id' in text
            checks['deterministic_policy']='_stable_id' in text and '_policy_for' in text
            checks['idempotent_policy']='idempotent_replay' in text
            checks['execution_not_triggered']='execution_allowed: bool = False' in text
            checks['external_action_blocked']='external_action_allowed: bool = False' in text
            checks['memory_write_blocked']='memory_write_allowed: bool = False' in text
        proc=subprocess.run([sys.executable,str(tests)],cwd=root,capture_output=True,text=True)
        checks['targeted_tests']=proc.returncode==0 and 'S55_TARGETED_TESTS_PASS 14/14' in proc.stdout
        comp=subprocess.run([sys.executable,'-m','compileall','-q','src','tests'],cwd=root,capture_output=True,text=True)
        checks['compileall']=comp.returncode==0
        if not all(checks.values()):
            raise RuntimeError('gate_contract_failed')
        sys.path.insert(0,str(root/'src'))
        from core.src.real_provider_failure_learning import FailureLearningCoordinator
        from core.src.adaptive_recovery_policy import AdaptiveRecoveryPolicyCoordinator, AdaptiveRecoveryPolicyRepository
        class Recovery:
            injected_model_failures=1; injected_search_failures=1; model_attempts=3; search_attempts=3
        lr=FailureLearningCoordinator().observe(Recovery(),recovery_run_id='S55-GATE-001')
        repo=AdaptiveRecoveryPolicyRepository(); c=AdaptiveRecoveryPolicyCoordinator(repo)
        a=c.select(lr); b=c.select(lr)
        checks['policy_contract_present']=a.policy.max_attempts>0 and a.policy.bounded
        checks['deterministic_policy']=a.policy.policy_id==b.policy.policy_id
        checks['idempotent_policy']=b.idempotent_replay and len(repo.snapshot())==1
        checks['policy_traceable']=lr.learning_signal.signal_id in b.learning_signal_id and any(x.startswith('learning:') for x in a.evidence_refs)
        checks['execution_not_triggered']=a.policy.execution_allowed is False
        checks['external_action_blocked']=a.policy.external_action_allowed is False
        checks['memory_write_blocked']=a.policy.memory_write_allowed is False
    except Exception as exc:
        notes.append(f'gate_runtime_error={type(exc).__name__}:{exc}')
    status='PASS' if all(checks.values()) else 'FAIL'
    print('S55_ADAPTIVE_RECOVERY_POLICY_PASS' if status=='PASS' else 'S55_ADAPTIVE_RECOVERY_POLICY_FAIL')
    print(json.dumps({'release':'O45-S55','status':status,'checks':checks,'path':'S54 failure learning -> adaptive recovery policy -> bounded retry/fallback -> next decision','execution_triggered':False,'external_action_executed':False,'memory_write_executed':False,'internet_facing_production_approval':False,'notes':notes},indent=2))
    if proc and proc.stdout: print(proc.stdout,end='')
    if proc and proc.stderr: print(proc.stderr,end='')
    if status!='PASS': raise SystemExit(1)
if __name__=='__main__': main()
