from __future__ import annotations
import ast, json, subprocess, sys
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    module=root/'src/core/src/real_provider_cost_aware_loop.py'
    tests=root/'tests/test_s57_real_provider_cost_aware_loop.py'
    s56=root/'src/core/src/cost_aware_recovery.py'
    s52=root/'src/core/src/real_provider_closed_loop.py'
    checks={k:False for k in [
        's52_present','s56_present','s57_module_present','targeted_tests_present',
        'real_provider_configuration','provider_model_live','provider_search_live',
        'provider_evidence_traceable','budget_policy_applied','provider_call_budget_enforced',
        'budget_units_enforced','transient_failure_recovered','closed_loop_two_cycles',
        'next_decision_reentered','new_trace_each_cycle','budget_exceeded_fail_closed',
        'execution_not_triggered','external_action_blocked','memory_write_blocked',
        'targeted_tests','compileall'
    ]}
    notes=[]; proc=None
    try:
        checks['s52_present']=s52.exists(); checks['s56_present']=s56.exists(); checks['s57_module_present']=module.exists(); checks['targeted_tests_present']=tests.exists()
        text=module.read_text(encoding='utf-8') if module.exists() else ''
        if module.exists():
            tree=ast.parse(text); classes={n.name for n in tree.body if isinstance(n,ast.ClassDef)}
            checks['budget_policy_applied']='CostAwareRecoveryCoordinator' in text and '_budget_for' in text
            checks['provider_call_budget_enforced']='max_provider_calls' in text and '_BudgetedCall' in text
            checks['budget_units_enforced']='s57_provider_budget_exceeded' in text and 'max_units' in text
            checks['execution_not_triggered']='execution_triggered=False' in text
            checks['external_action_blocked']='external_action_executed=False' in text
            checks['memory_write_blocked']='memory_write_executed=False' in text
        env=dict(__import__("os").environ); env["PYTHONPATH"]=str(root/"src") + __import__("os").pathsep + env.get("PYTHONPATH", ""); proc=subprocess.run([sys.executable,str(tests)],cwd=root,capture_output=True,text=True,env=env)
        checks['targeted_tests']=proc.returncode==0 and 'S57_TARGETED_TESTS_PASS 16/16' in proc.stdout
        comp=subprocess.run([sys.executable,'-m','compileall','-q','src','tests'],cwd=root,capture_output=True,text=True,env=env)
        checks['compileall']=comp.returncode==0
        if not all(checks[k] for k in ['s52_present','s56_present','s57_module_present','targeted_tests','compileall']):
            raise RuntimeError('gate_contract_failed')
        from core.src.live_providers import provider_configuration_status
        cfg=provider_configuration_status(); checks['real_provider_configuration']=cfg.get('status')=='CONFIGURED'
        if not checks['real_provider_configuration']:
            raise RuntimeError('real_provider_configuration_incomplete')
        from core.src.real_provider_cost_aware_loop import RealProviderCostAwareLoopCoordinator
        c=RealProviderCostAwareLoopCoordinator(max_budget_units=12, inject_model_failures=1, inject_search_failures=1)
        out=c.run(project_id='P-S57-GATE')
        checks['provider_model_live']=all(x.provider_model_live and len(x.model_hash)==64 for x in out.cycles)
        checks['provider_search_live']=all(x.provider_search_live and x.search_result_count>0 and len(x.search_hash)==64 for x in out.cycles)
        snaps=c.closed_loop.trace_snapshot()
        refs=[]
        for x in out.cycles: refs.extend(next(v for v in snaps.values() if v.trace_id == x.trace_id).evidence_refs)
        checks['provider_evidence_traceable']=any(r.startswith('REAL-MODEL-') for r in refs) and any(r.startswith('REAL-SEARCH-') for r in refs) and any(r.startswith('BUDGET-') for r in refs)
        checks['transient_failure_recovered']=out.cycles[0].status=='SUCCESS' and out.cycles[0].model_stats.failures_injected==1 and out.cycles[0].search_stats.failures_injected==1
        checks['closed_loop_two_cycles']=out.closed_loop_two_cycles and len(out.cycles)==2
        checks['next_decision_reentered']=out.next_decision_reentered
        checks['new_trace_each_cycle']=out.new_trace_each_cycle
        checks['execution_not_triggered']=out.execution_triggered is False
        checks['external_action_blocked']=out.external_action_executed is False
        checks['memory_write_blocked']=out.memory_write_executed is False
        try:
            RealProviderCostAwareLoopCoordinator(max_budget_units=1, inject_model_failures=1, inject_search_failures=1).run(project_id='P-S57-BLOCK')
        except RuntimeError as exc:
            checks['budget_exceeded_fail_closed']='s57_budget_exceeded_fail_closed' in str(exc)
        except Exception as exc:
            notes.append(f'budget_block_error={type(exc).__name__}:{exc}')
        else:
            checks['budget_exceeded_fail_closed']=False
    except Exception as exc:
        notes.append(f'gate_runtime_error={type(exc).__name__}:{exc}')
    status='PASS' if all(checks.values()) else 'FAIL'
    print('S57_REAL_PROVIDER_COST_AWARE_LOOP_PASS' if status=='PASS' else 'S57_REAL_PROVIDER_COST_AWARE_LOOP_FAIL')
    print(json.dumps({'release':'O45-S57','status':status,'checks':checks,'path':'S56 cost-aware recovery -> real provider calls -> bounded budget enforcement -> closed-loop cycle 1 -> persisted/re-entry cycle 2','external_action_executed':False,'memory_write_executed':False,'internet_facing_production_approval':False,'notes':notes},indent=2))
    if proc and proc.stdout: print(proc.stdout,end='')
    if proc and proc.stderr: print(proc.stderr,end='')
    if status!='PASS': raise SystemExit(1)

if __name__=='__main__': main()
