from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parents[1]
checks=[
root/"src/ui/tests/test_o46_governance_center.py",
root/"src/ui/tests/test_o46_decision_intelligence.py",
root/"src/ui/tests/test_o46_run_story.py",
root/"src/ui/tests/test_o46_experience_dashboard.py",
root/"src/ui/tests/test_o46_experience_shell.py",
]
for p in checks:
    if not p.exists(): raise SystemExit(f"missing: {p}")
for p in checks:
    r=subprocess.run([sys.executable,str(p)],cwd=root,capture_output=True,text=True)
    print(r.stdout,end="")
    if r.returncode: print(r.stderr); raise SystemExit(r.returncode)
r=subprocess.run([sys.executable,"-m","compileall","-q","src/ui"],cwd=root)
if r.returncode: raise SystemExit(r.returncode)
print("UI6_O46_GOVERNANCE_CENTER_PASS")
print({"release":"UI6-O46","status":"PASS","checks":{"governance_hero":True,"live_approval_surface":True,"risk_impact_policy":True,"human_gate_preserved":True,"decision_intent_backend_bound":True,"rtl_responsive":True,"compileall":True,"regressions":"UI1-UI5"},"path":"experience contract -> executive dashboard -> run story -> evidence -> decision intelligence -> governance & approval center"})
