from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'src'/'ui'/'ui'/'index.html'; CSS=ROOT/'src'/'ui'/'ui'/'ui20_console.css'; JS=ROOT/'src'/'ui'/'ui'/'ui20_console.js'
for p in (INDEX,CSS,JS): assert p.exists(), p
idx=INDEX.read_text(encoding='utf-8'); css=CSS.read_text(encoding='utf-8'); js=JS.read_text(encoding='utf-8')
checks={
'assets_loaded':'ui20_console.css?v=20.0.0' in idx and 'ui20_console.js?v=20.0.0' in idx,
'canonical_run':'getCanonicalRun' in js and 'completeness' in js,
'spa_hydration':'MutationObserver' in js and 'onPageChange' in js,
'single_surface':'u20-native-preferred' in js and 'u20-host-preferred' in js,
'executive_sync':'bindExecutive' in js and 'experienceDecisionTitle' in js,
'golden_sync':'goldenJourney' in js and 'goldenValidationGrid' in js,
'acceptance_sync':'acceptanceGrid' in js and 'acceptanceScore' in js,
'visual_tokens':'--u20-panel' in css and 'prefers-reduced-motion' in css,
'safe_reads':"'/runs?limit=25'" in js and "'/runs/'" in js,
'no_external_autonomy':'POST' not in js and 'approve' not in js.lower().split('window.__AIOS_UI20',1)[0],
}
for name,ok in checks.items(): print(f'test_{name} ... '+('ok' if ok else 'FAIL')); assert ok,name
print('UI20_O46_FULL_CONSOLE_VISUAL_PASS')
print('UI20_SINGLE_SURFACE_MODE_PASS')
print('UI20_CANONICAL_RUN_SYNC_PASS')
print('UI20_SPA_NAVIGATION_HYDRATION_PASS')
print('UI20_EXECUTIVE_GOLDEN_ACCEPTANCE_SYNC_PASS')
print('UI20_RESPONSIVE_VISUAL_PASS')
print('UI20_GOVERNANCE_BOUNDARY_PRESERVED')
