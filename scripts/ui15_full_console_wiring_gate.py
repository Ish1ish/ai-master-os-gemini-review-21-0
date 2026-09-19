import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'ui'))

suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_ui15_full_console_wiring')
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print('UI15_O46_FULL_CONSOLE_WIRING_PASS')
print('UI15_NAV_PAGES_WIRED 21')
print('UI15_LIVE_READ_ENDPOINTS_WIRED')
print('UI15_SEMANTIC_MAPPING_DISTINCT')
print('UI15_EXPLICIT_MUTATIONS_ONLY')
print('UI15_EMPTY_LOADING_ERROR_STATES')
print('UI15_GOVERNANCE_BOUNDARY_PRESERVED')
print('UI15_RESPONSIVE_SURFACES_INCLUDED')
