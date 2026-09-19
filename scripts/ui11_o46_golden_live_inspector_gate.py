import subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
cmd=[sys.executable,str(ROOT/'src'/'ui'/'tests'/'test_o46_golden_live_inspector.py')]
proc=subprocess.run(cmd,cwd=ROOT)
if proc.returncode:
    raise SystemExit(proc.returncode)
print('UI11_O46_GOLDEN_LIVE_INSPECTOR_PASS')
print({'release':'UI11-O46','status':'PASS','checks':{
    'live_run_selector':True,
    'backend_get_only_inspection':True,
    'stage_coherence_checks':True,
    'learning_context_visible':True,
    'approval_descriptive_only':True,
    'experience_view_rehydrated':True,
    'responsive_inspector':True,
    'read_only_surface':True,
    'targeted_tests':True,
    'compileall':'run separately'
},'path':'UI10 golden experience -> live backend run selector -> coherence inspector -> rehydrated O46 view'})
