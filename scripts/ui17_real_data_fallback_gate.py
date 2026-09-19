import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
suite = unittest.defaultTestLoader.discover(str(ROOT / 'src' / 'ui' / 'tests'), pattern='test_ui17_real_data_fallback.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print('UI17_O46_REAL_DATA_FALLBACK_PASS')
print('UI17_PREFERRED_RUN_REHYDRATION_FIRST')
print('UI17_RUN_LIST_LIMIT_ALIGNED')
print('UI17_GOVERNANCE_BOUNDARY_PRESERVED')
