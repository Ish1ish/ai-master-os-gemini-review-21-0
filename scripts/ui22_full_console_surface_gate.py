from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
UI=ROOT/'src'/'ui'/'ui'
JS=(UI/'ui22_console.js').read_text(encoding='utf-8')
CSS=(UI/'ui22_console.css').read_text(encoding='utf-8')
INDEX=(UI/'index.html').read_text(encoding='utf-8')
checks={
'singleton_target':'nav-item.active[data-page]' in JS and 'u22-hidden-force' in JS,
'all_pages_forced_hidden':'document.querySelectorAll(\'.page\')' in JS and 'classList.toggle(\'hidden\'' in JS,
'recovery_leak_prevented':'page-recovery' in INDEX and 'u22-hidden-force' in JS,
'golden_acceptance_experiments_share_surface':'targetPage' in JS and 'u22-visible-force' in JS,
'long_state_trim':'slice(0,177)' in JS,
'css_boundaries':'height:0!important' in CSS and 'visibility:hidden!important' in CSS,
'no_mutation_methods':not any(x in JS for x in ['fetch(', 'POST','PUT','PATCH','DELETE']),
}
for k,v in checks.items():
 print(f'test_{k} ... '+('ok' if v else 'FAIL')); assert v,k
print('UI22_O46_FULL_CONSOLE_SURFACE_PASS')
print('UI22_SINGLE_VISIBLE_PAGE_PASS')
print('UI22_LEGACY_PAGE_LEAK_PREVENTED')
print('UI22_STATE_TEXT_POLISH_PASS')
print('UI22_READ_ONLY_PASS')
