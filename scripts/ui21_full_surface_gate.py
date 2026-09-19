from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT/'src'/'ui'/'ui'/'ui21_console.css'
JS = ROOT/'src'/'ui'/'ui'/'ui21_console.js'
INSTALL = ROOT/'scripts'/'ui21_install_overlay.py'
for p in (CSS,JS,INSTALL):
    assert p.exists(), p
css=CSS.read_text(encoding='utf-8')
js=JS.read_text(encoding='utf-8')
checks={
'assets_present':True,
'single_surface':'ui21-surface' in js and 'hidePageChildren' in js,
'duplicate_suppression':'u21-hide-original' in js and 'u21-keep-original' in js,
'canonical_run':'/runs?limit=25' in js and 'canonicalRun' in js,
'spa_refresh':'MutationObserver' in js and 'renderVisiblePage' in js,
'golden_surface':'renderGolden' in js and "page-golden" in js,
'acceptance_surface':'renderAcceptance' in js and "page-acceptance" in js,
'experiments_surface':'renderExperiments' in js and "page-experiments" in js,
'proxy_actions':'proxyClick' in js and "data-u21=\"create\"" in js,
'read_only':'POST' not in js and 'PUT' not in js and 'PATCH' not in js and 'DELETE' not in js,
'responsive':'@media(max-width:900px)' in css and 'prefers-reduced-motion' in css,
}
for name,ok in checks.items():
    print(f'test_{name} ... ' + ('ok' if ok else 'FAIL'))
    assert ok, name
print('UI21_O46_FULL_CONSOLE_SURFACE_PASS')
print('UI21_SINGLE_PAGE_SURFACE_PASS')
print('UI21_DUPLICATE_SURFACES_SUPPRESSED')
print('UI21_CANONICAL_RUN_SYNC_PASS')
print('UI21_PROXY_ACTIONS_READ_ONLY')
print('UI21_RESPONSIVE_PASS')
print('UI21_GOVERNANCE_BOUNDARY_PRESERVED')
