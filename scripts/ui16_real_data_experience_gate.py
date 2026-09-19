from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / 'src' / 'ui' / 'tests' / 'test_ui16_real_data_experience.py'

r = subprocess.run([sys.executable, '-m', 'unittest', str(TEST), '-v'], cwd=ROOT)
if r.returncode != 0:
    raise SystemExit(r.returncode)
print('UI16_O46_REAL_DATA_EXPERIENCE_PASS')
print('UI16_LATEST_RUN_REHYDRATION_INCLUDED')
print('UI16_EXECUTIVE_SURFACE_DATA_BOUND')
print('UI16_SEMANTIC_FIELDS_PRESERVED')
print('UI16_GOVERNANCE_BOUNDARY_PRESERVED')
print('UI16_EMPTY_ERROR_SAFE')
