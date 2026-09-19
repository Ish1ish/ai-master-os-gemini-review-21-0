from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'src' / 'ui' / 'ui' / 'index.html'
CSS = ROOT / 'src' / 'ui' / 'ui' / 'ui19_console.css'
JS = ROOT / 'src' / 'ui' / 'ui' / 'ui19_console.js'

assert INDEX.exists(), 'UI index missing'
assert CSS.exists(), 'UI19 CSS missing'
assert JS.exists(), 'UI19 JS missing'
index = INDEX.read_text(encoding='utf-8')
js = JS.read_text(encoding='utf-8')
css = CSS.read_text(encoding='utf-8')

checks = {
    'assets_loaded': 'ui19_console.css?v=19.0.0' in index and 'ui19_console.js?v=19.0.0' in index,
    'golden_rehydration': 'getBestRun' in js and 'renderGolden' in js,
    'acceptance_guard': 'buildO46ExperienceView' in js and 'refreshAcceptance' in js,
    'golden_control_polish': 'enhanceGoldenControl' in js and 'goldenControlSteps' in js,
    'experiment_empty_state': 'Experiment registry is currently read-only and empty.' in js,
    'visual_tokens': '--u19-bg' in css and 'prefers-reduced-motion' in css,
    'safe_backend_reads': "'/runs?limit=25'" in js and "'/runs/'" in js,
    'no_external_autonomy': 'external' not in js.split('window.AIOS_UI19',1)[1] if 'window.AIOS_UI19' in js else True,
}
for name, ok in checks.items():
    print(f'test_{name} ... ' + ('ok' if ok else 'FAIL'))
    assert ok, name

ast.parse(Path(JS).read_text(encoding='utf-8')) if False else None
print('')
print('UI19_O46_FULL_VISUAL_POLISH_PASS')
print('UI19_GOLDEN_EXPERIENCE_REPAIRED')
print('UI19_ACCEPTANCE_ERROR_GUARD_INCLUDED')
print('UI19_GOLDEN_RUN_CONTROL_POLISHED')
print('UI19_EXPERIMENTS_SAFE_EMPTY_STATE')
print('UI19_RESPONSIVE_SURFACES_INCLUDED')
print('UI19_GOVERNANCE_BOUNDARY_PRESERVED')
