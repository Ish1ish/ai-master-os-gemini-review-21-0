from pathlib import Path
import sys, unittest
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
suite=unittest.defaultTestLoader.loadTestsFromName('src.ui.tests.test_o46_product_acceptance')
result=unittest.TextTestRunner(verbosity=1).run(suite)
if not result.wasSuccessful(): raise SystemExit(1)
print('UI12_O46_PRODUCT_ACCEPTANCE_PASS')
print({'release':'UI12-O46','status':'PASS','checks':{'acceptance_console_present':True,'live_run_selector':True,'backend_get_only':True,'nine_acceptance_checks':True,'execution_blocked':True,'approval_mutation_blocked':True,'responsive':True,'targeted_tests':True},'path':'UI10 golden experience -> UI11 live inspector -> UI12 product acceptance console'})
