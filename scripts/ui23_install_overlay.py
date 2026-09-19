from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'src' / 'ui' / 'ui'
INDEX = UI / 'index.html'
if not INDEX.exists():
    raise SystemExit('Missing UI index')
text = INDEX.read_text(encoding='utf-8')
needle = '''      <section class="page hidden" id="page-recovery">'''
if needle not in text:
    raise SystemExit('Recovery page marker not found')
# Remove the exact stray duplicate reconciliation block that sits outside the Recovery page.
stray = '''          <section class="card"><div class="card-head"><div><div class="eyebrow">RECONCILIATION PLAYBOOK</div><h3>Safe response</h3></div></div><div class="stack"><div class="guide-step mini"><span>1</span><div><b>Inspect receipt</b><small>Confirm exact action, request hash and lease state.</small></div></div><div class="guide-step mini"><span>2</span><div><b>Check external system</b><small>Determine whether the side effect actually happened.</small></div></div><div class="guide-step mini"><span>3</span><div><b>Reconcile</b><small>Record the observed outcome before any retry decision.</small></div></div></div></section>\n        </div>\n      </section>'''
count = text.count(stray)
if count != 1:
    raise SystemExit(f'Expected one stray recovery block, found {count}')
text = text.replace(stray, '      </section>', 1)
# Add a deterministic structure marker for future checks.
marker = '<meta name="aios-ui23-structural-repair" content="recovery-duplicate-removed" />'
if marker not in text:
    text = text.replace('</head>', f'  {marker}\n</head>', 1)
INDEX.write_text(text, encoding='utf-8')
print('UI23_OVERLAY_INSTALLED')
print('UI23_RECOVERY_DUPLICATE_REMOVED')
print('UI23_HTML_STRUCTURE_REPAIRED')
print('UI23_SINGLE_PAGE_LEAK_SOURCE_REMOVED')
