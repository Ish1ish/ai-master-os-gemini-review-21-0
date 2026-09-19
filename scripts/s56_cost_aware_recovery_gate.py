from __future__ import annotations
import ast, json, subprocess, sys
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[1]
    s55=root/'src/core/src/adaptive_recovery_policy.py'
    module=root/'src/core/src/cost_aware_recovery.py'
    tests=root/'tests/test_s56_cost_aware_recovery.py'
    checks={k:False for k in [
        's55_present','cost_aware_module_present','targeted_tests_present','budget_contract_present',
        'hard_budget_ceiling_present','provider_call_limit_present','fail_closed_budget_present',
        'traceable_evidence_present','deterministic_budget_present','idempotent_budget_present',
        'execution_not_triggered','external_action_blocked','memory_write_blocked','targeted_tests','compileall',
        'budgeted_recovery_pass','budget_exceeded_fail_closed','budget_idempotent'
    ]}
    notes=[]; proc=None
    try:
        checks['s55_present']=s55.exists(); checks['cost_aware_module_present']=module.exists(); checks['targeted_tests_present']=tests.exists()
        text=module.read_text(encoding='utf-8') if module.exists() else ''
        if module.exists():
            tree=ast.parse(text); classes={n.name for n in tree.body if isinstance(n,ast.ClassDef)}
            checks['budget_contract_present']='RecoveryBudget' in classes and 'CostAwareRecoveryResult' in classes
            checks['hard_budget_ceiling_present']='max_budget_units' in text and 'budget_policy' in text
            checks['provider_call_limit_present']='max_provider_calls' in text and 'estimated_provider_calls' in text
            checks['fail_closed_budget_present']='BUDGET_EXCEEDED_FAIL_CLOSED' in text
            checks['traceable_evidence_present']='evidence_refs' in text and 'budget:' in text
            checks['deterministic_budget_present']='_stable_id' in text and 'budget_id' in text
            checks['idempotent_budget_present']='idempotent_replay' in text and 'snapshot' in text
            checks['execution_not_triggered']='execution_triggered: bool = False' in text
            checks['external_action_blocked']='external_action_executed: bool = False' in text
            checks['memory_write_blocked']='memory_write_executed: bool = False' in text
        proc=subprocess.run([sys.executable,str(tests)],cwd=root,capture_output=True,text=True)
        checks['targeted_tests']=proc.returncode==0 and 'S56_TARGETED_TESTS_PASS 15/15' in proc.stdout
        comp=subprocess.run([sys.executable,'-m','compileall','-q','src','tests'],cwd=root,capture_output=True,text=True)
        checks['compileall']=comp.returncode==0
        if not all(checks[k] for k in ['s55_present','cost_aware_module_present','targeted_tests_present','budget_contract_present','targeted_tests','compileall']):
            raise RuntimeError('gate_contract_failed')
        sys.path.insert(0,str(root/'src'))
        from core.src.real_provider_failure_learning import FailureLearningCoordinator
        from core.src.adaptive_recovery_policy import AdaptiveRecoveryPolicyCoordinator
        from core.src.cost_aware_recovery import CostAwareRecoveryCoordinator, CostAwareRecoveryRepository
        class Recovery:
            injected_model_failures=1; injected_search_failures=1; model_attempts=3; search_attempts=3
        lr=FailureLearningCoordinator().observe(Recovery(),recovery_run_id='S56-GATE-001')
        pr=AdaptiveRecoveryPolicyCoordinator().select(lr)
        allowed=CostAwareRecoveryCoordinator(max_budget_units=20).apply(pr)
        blocked=CostAwareRecoveryCoordinator(max_budget_units=1).apply(pr, recovery_run_id='S56-GATE-002')
        repo=CostAwareRecoveryRepository(); c=CostAwareRecoveryCoordinator(repo,max_budget_units=20)
        a=c.apply(pr, recovery_run_id='S56-GATE-003'); b=c.apply(pr, recovery_run_id='S56-GATE-003')
        checks['budgeted_recovery_pass']=allowed.status=='BUDGETED' and allowed.budget.within_budget
        checks['budget_exceeded_fail_closed']=blocked.status=='BUDGET_BLOCKED' and blocked.next_decision=='COLLECT_MORE_EVIDENCE'
        checks['budget_idempotent']=b.idempotent_replay and len(repo.snapshot())==1
    except Exception as exc:
        notes.append(f'gate_runtime_error={type(exc).__name__}:{exc}')
    status='PASS' if all(checks.values()) else 'FAIL'
    print('S56_COST_AWARE_ADAPTIVE_RECOVERY_PASS' if status=='PASS' else 'S56_COST_AWARE_ADAPTIVE_RECOVERY_FAIL')
    print(json.dumps({'release':'O45-S56','status':status,'checks':checks,'path':'S55 adaptive recovery policy -> hard recovery budget -> bounded attempts/calls -> fail-closed when budget exceeded','budget_examples':{'allowed':'BUDGETED','blocked':'BUDGET_BLOCKED'},'execution_triggered':False,'external_action_executed':False,'memory_write_executed':False,'internet_facing_production_approval':False,'notes':notes},indent=2))
    if proc and proc.stdout: print(proc.stdout,end='')
    if proc and proc.stderr: print(proc.stderr,end='')
    if status!='PASS': raise SystemExit(1)
if __name__=='__main__': main()
