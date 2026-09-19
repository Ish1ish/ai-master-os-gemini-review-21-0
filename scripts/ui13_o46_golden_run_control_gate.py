from pathlib import Path
import sys, unittest
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
suite=unittest.defaultTestLoader.loadTestsFromName('src.ui.tests.test_o46_golden_run_control')
result=unittest.TextTestRunner(verbosity=1).run(suite)
if not result.wasSuccessful(): raise SystemExit(1)
print('UI13_O46_GOLDEN_RUN_CONTROL_PASS')
print({'release':'UI13-O46','status':'PASS','checks':{'control_page_present':True,'explicit_create':True,'explicit_execute':True,'backend_rehydration':True,'learning_visible':True,'approval_descriptive':True,'no_auto_execute':True,'responsive':True,'targeted_tests':True},'path':'UI12 acceptance -> explicit Golden Run control -> backend create -> explicit governed execute -> live O46 rehydration'})
