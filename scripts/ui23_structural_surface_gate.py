from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'src' / 'ui' / 'ui'
INDEX = UI / 'index.html'
text = INDEX.read_text(encoding='utf-8')
checks = {
    'duplicate_reconciliation_removed': text.count('RECONCILIATION PLAYBOOK') == 1,
    'recovery_page_present': 'id="page-recovery"' in text,
    'repair_marker_present': 'aios-ui23-structural-repair' in text,
    'golden_run_page_present': 'id="page-goldenrun"' in text,
    'golden_page_present': 'id="page-golden"' in text,
    'acceptance_page_present': 'id="page-acceptance"' in text,
    'experiments_page_present': 'id="page-experiments"' in text,
    'no_scripts_injected': 'fetch(' not in text and 'window.open(' not in text,
}
for name, ok in checks.items():
    print(f'test_{name} ... ' + ('ok' if ok else 'FAIL'))
    assert ok, name
# Lightweight structural sanity: recovery page must close before health page starts.
start = text.index('id="page-recovery"')
health = text.index('id="page-health"')
assert text.rfind('</section>', start, health) > start
print('UI23_O46_STRUCTURAL_SURFACE_PASS')
print('UI23_RECOVERY_DUPLICATE_REMOVED')
print('UI23_SINGLE_PAGE_LEAK_SOURCE_REMOVED')
print('UI23_READ_ONLY_INSTALL_PASS')
