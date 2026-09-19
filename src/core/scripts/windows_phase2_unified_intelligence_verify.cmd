@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 exit /b 1
python -m compileall -q .
if errorlevel 1 exit /b 1
python scripts\unified_decision_intelligence_smoke.py
if errorlevel 1 exit /b 1
python -c "from src.unified_decision_intelligence import UnifiedDecisionIntelligence as U; print('PHASE 2 CONTRACT CHECK PASS' if U.plan(project_id='c',context={},candidates=[],uncertainty='LOW',reliability='STRONG',resource_pressure='NORMAL',latency_posture='NORMAL',cost_posture='WITHIN_BUDGET')['status']=='HOLD' else 'PHASE 2 CONTRACT CHECK FAIL')"
if errorlevel 1 exit /b 1
python -c "from src.unified_decision_intelligence import UnifiedDecisionIntelligence as U; x=U.plan(project_id='c',context={},candidates=[{'provider':'a','tool':'t','score':1}],uncertainty='HIGH',reliability='UNKNOWN',resource_pressure='CRITICAL',latency_posture='SLOW',cost_posture='OVER_BUDGET'); assert x['status']=='REFINE' and not x['external_action_executed'] and x['governance_authority']=='POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE'; print('PHASE 2 SAFETY BOUNDARY CHECK PASS')"
if errorlevel 1 exit /b 1
echo ALL PHASE 2 UNIFIED DECISION INTELLIGENCE CHECKS PASSED.
endlocal
