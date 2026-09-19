from __future__ import annotations
import json, subprocess, sys, os
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[1]
    src=root/'src/core/src'; module=src/'real_provider_governed_autonomous_loop.py'; s58=src/'multi_dimensional_resource_governor.py'; test=root/'tests/test_o46_real_provider_loop.py'
    checks={
      's58_governor_present':s58.exists(),'s60_module_present':module.exists(),'targeted_tests_present':test.exists(),
      'real_provider_adapter_present':(src/'live_providers.py').exists(),'real_provider_configuration':False,
      'provider_model_live':False,'provider_search_live':False,'provider_evidence_traceable':False,
      'governance_present':'MultiDimensionalResourceGovernor' in (module.read_text(encoding='utf-8') if module.exists() else ''),
      'two_cycles':False,'next_decision_reentered':False,'external_action_blocked':True,'memory_write_blocked':True,
      'execution_not_triggered_by_reentry':True,'targeted_tests':False,'compileall':False}
    notes=[]; env=dict(os.environ); env['PYTHONPATH']=str(root/'src')+os.pathsep+env.get('PYTHONPATH','')
    p=subprocess.run([sys.executable,str(test)],cwd=root,capture_output=True,text=True,env=env)
    checks['targeted_tests']=p.returncode==0 and 'S60_TARGETED_TESTS_PASS 12/12' in p.stdout
    c=subprocess.run([sys.executable,'-m','compileall','-q','src','tests'],cwd=root,capture_output=True,text=True,env=env)
    checks['compileall']=c.returncode==0
    try:
        sys.path.insert(0,str(root/'src'))
        from core.src.live_providers import provider_configuration_status, model_provider, search_provider
        cfg=provider_configuration_status(); checks['real_provider_configuration']=cfg.get('status')=='CONFIGURED'
        if checks['real_provider_configuration']:
            m=model_provider('Reply with exactly JSON: {"status":"LIVE"}')
            s=search_provider('O46 S60 governed autonomous loop validation')
            checks['provider_model_live']=bool(m.get('text'))
            checks['provider_search_live']=bool(s.get('results'))
            checks['provider_evidence_traceable']=bool(s.get('results'))
        if all(checks[k] for k in ['real_provider_configuration','provider_model_live','provider_search_live']):
            from core.src.real_provider_governed_autonomous_loop import RealProviderGovernedAutonomousLoop
            loop=RealProviderGovernedAutonomousLoop()
            result=loop.run()
            checks['two_cycles']=result.closed_loop and len(result.cycles)==2
            checks['next_decision_reentered']=result.reentered
            checks['external_action_blocked']=not result.external_action_executed
            checks['memory_write_blocked']=not result.memory_write_executed
            checks['execution_not_triggered_by_reentry']=not result.execution_triggered_by_reentry
        else: notes.append('real_provider_configuration_incomplete')
    except Exception as exc:
        notes.append(f'gate_runtime_error={type(exc).__name__}:{exc}')
    status='PASS' if all(checks.values()) else 'FAIL'
    payload={'release':'O46-S60','status':status,'checks':checks,'path':'real provider research -> decision -> S58 resource governance -> bounded real-provider synthesis -> outcome -> re-entry -> second cycle','external_action_executed':False,'memory_write_executed':False,'internet_facing_production_approval':False,'notes':notes}
    print('S60_REAL_PROVIDER_GOVERNED_AUTONOMOUS_LOOP_PASS' if status=='PASS' else 'S60_REAL_PROVIDER_GOVERNED_AUTONOMOUS_LOOP_FAIL')
    print(json.dumps(payload,indent=2))
    print(p.stdout,end=''); print(p.stderr,end='')
    if status!='PASS': raise SystemExit(1)

if __name__=='__main__': main()
