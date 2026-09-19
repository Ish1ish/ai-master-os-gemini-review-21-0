import subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
cmd=[sys.executable,'-m','unittest','discover','-s','src/ui/tests','-p','test_o46_evidence_explorer.py']
res=subprocess.run(cmd,cwd=ROOT)
if res.returncode!=0: sys.exit(res.returncode)
print('UI4_O46_EVIDENCE_EXPLORER_PASS')
print({'release':'UI4-O46','status':'PASS','checks':{'evidence_map_present':True,'claim_source_decision_trace':True,'backend_derived_guardrails':True,'responsive_visual_layer':True,'targeted_tests':True},'path':'unified experience contract -> executive dashboard -> run story -> evidence map -> traceable decision context'})
