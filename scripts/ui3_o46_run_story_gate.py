from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
cmd=[sys.executable,'-m','unittest','src.ui.tests.test_o46_run_story','src.ui.tests.test_o46_experience_dashboard','src.ui.tests.test_o46_experience_shell']
res=subprocess.run(cmd,cwd=ROOT)
if res.returncode!=0: raise SystemExit(res.returncode)
print('UI3_O46_RUN_STORY_PASS')
print({'release':'UI3-O46','status':'PASS','checks':{'run_story_present':True,'nine_stage_journey':True,'backend_derived':True,'interactive_stage_detail':True,'ui2_regression':True},'path':'unified experience contract -> executive dashboard -> interactive run story -> stage explainability'})
