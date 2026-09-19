@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"

echo [1/5] RUNNING FULL CORE REGRESSION + V0.8 TESTS
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :fail

echo [2/5] COMPILEALL
python -m compileall -q src scripts tests
if errorlevel 1 goto :fail

echo [3/5] V0.8 BOUNDED SELF-OPTIMIZATION SMOKE
python scripts\bounded_self_optimization_smoke.py
if errorlevel 1 goto :fail

echo [4/5] V0.8 CONTRACT CHECK
python -c "from src.bounded_self_optimization import BoundedSelfOptimizer; p=BoundedSelfOptimizer.propose(project_id='C', proposal={'component':'routing','change_type':'ROUTING','current_value':'A','proposed_value':'B','rationale':'r','evidence_refs':['E'],'rollback_plan':'restore A','apply_mode':'GOVERNED_APPLY'}); assert p['status']=='PROPOSED'; s=BoundedSelfOptimizer.simulate(p,baseline={'quality':.7},simulated={'quality':.9},sample_count=10,uncertainty={'uncertainty_band':'LOW'}); e=BoundedSelfOptimizer.evaluate(p,s,success_metrics=['quality'],minimum_improvement=.1); g=BoundedSelfOptimizer.govern(p,e); assert e['decision']=='GO'; assert g['decision']=='REVIEW'; print('V0.8 CONTRACT CHECK PASS')"
if errorlevel 1 goto :fail

echo [5/5] V0.8 SAFETY BOUNDARY CHECK
python -c "from src.bounded_self_optimization import BoundedSelfOptimizer; p=BoundedSelfOptimizer.propose(project_id='C', proposal={'component':'routing','change_type':'ROUTING','current_value':'A','proposed_value':'B','rationale':'r','evidence_refs':['E'],'rollback_plan':'restore A','apply_mode':'SIMULATION_ONLY'}); s=BoundedSelfOptimizer.simulate(p,baseline={'quality':.7},simulated={'quality':.9},sample_count=10,uncertainty={'uncertainty_band':'LOW'}); e=BoundedSelfOptimizer.evaluate(p,s,success_metrics=['quality'],minimum_improvement=.1); g=BoundedSelfOptimizer.govern(p,e); a=BoundedSelfOptimizer.apply(p,e,g,approved=True,version='v2',previous_version='v1'); assert a['status']=='REJECTED'; assert a['reason']=='simulation_only_change_cannot_be_applied'; print('V0.8 SAFETY BOUNDARY CHECK PASS')"
if errorlevel 1 goto :fail

echo.
echo ALL V0.8 BOUNDED SELF-OPTIMIZATION CHECKS PASSED.
exit /b 0

:fail
echo.
echo V0.8 VERIFICATION FAILED.
exit /b 1
