import importlib.util
import py_compile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / 'src' / 'ui' / 'tests' / 'test_o46_decision_intelligence.py'
APP = ROOT / 'src' / 'ui' / 'ui' / 'app.js'
HTML = ROOT / 'src' / 'ui' / 'ui' / 'index.html'
CSS = ROOT / 'src' / 'ui' / 'ui' / 'styles.css'

spec = importlib.util.spec_from_file_location('ui5_tests', TEST)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
suite = __import__('unittest').defaultTestLoader.loadTestsFromModule(mod)
result = __import__('unittest').TextTestRunner(verbosity=0).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
for p in (ROOT / 'src' / 'ui').rglob('*.py'):
    py_compile.compile(str(p), doraise=True)
for p in (APP, HTML, CSS):
    if not p.exists() or not p.read_text(encoding='utf-8').strip():
        raise SystemExit(f'missing or empty file: {p}')
print('UI5_O46_DECISION_INTELLIGENCE_PASS')
print({'release':'UI5-O46','status':'PASS','checks':{'decision_intelligence_present':True,'backend_derived':True,'why_direction':True,'next_step_surface':True,'rtl_responsive':True,'targeted_tests':True,'compileall':True},'path':'unified experience contract -> executive dashboard -> run story -> evidence map -> explainable decision intelligence -> next action'})
