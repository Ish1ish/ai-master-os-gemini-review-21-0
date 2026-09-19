@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"

python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :fail

python -m compileall -q src scripts tests
if errorlevel 1 goto :fail

python scripts\production_intelligence_smoke.py
if errorlevel 1 goto :fail

python -c "from src.production_intelligence import ProductionIntelligence as P; o={'provider':'A','tool':'T','observed_at':'2026-09-12T00:00:00Z','cost_usd':.02,'latency_ms':120,'success_rate':.99,'sample_count':50,'cpu_pct':30,'memory_pct':40,'freshness':'FRESH','evidence_refs':['E']}; a=P.assess([o],max_latency_ms=300,max_cost_usd=.10); r=P.recommend(project_id='C',context={'risk_class':'LOW'},assessment=a,candidates=[{'provider':'A','tool':'T','cost_usd':.02,'latency_ms':120,'success_rate':.99}]); assert r['status']=='ADVISORY'; assert r['requires_governance'] is True; assert r['external_action_executed'] is False; print('V0.9 CONTRACT CHECK PASS')"
if errorlevel 1 goto :fail

python -c "from src.production_intelligence import ProductionIntelligence as P; a=P.assess([],max_latency_ms=300,max_cost_usd=.10); r=P.recommend(project_id='C',context={},assessment=a,candidates=[]); assert a['latency_posture']=='UNKNOWN'; assert a['cost_posture']=='UNKNOWN'; assert r['action']=='HOLD_AND_COLLECT_TELEMETRY'; assert r['external_action_executed'] is False; print('V0.9 SAFETY BOUNDARY CHECK PASS')"
if errorlevel 1 goto :fail

echo.
echo ALL V0.9 PRODUCTION INTELLIGENCE CHECKS PASSED.
exit /b 0

:fail
echo.
echo V0.9 VERIFICATION FAILED.
exit /b 1
