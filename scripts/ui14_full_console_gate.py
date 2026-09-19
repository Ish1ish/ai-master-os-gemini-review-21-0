
from pathlib import Path
import subprocess,sys,re
root=Path(__file__).resolve().parents[1]
ui=root/'src/ui/ui'
assert (ui/'ux14_console.js').exists()
assert (ui/'ux14_console.css').exists()
idx=(ui/'index.html').read_text(encoding='utf-8')
js=(ui/'ux14_console.js').read_text(encoding='utf-8')
nav=re.findall(r'data-page="([^"]+)"',idx)
missing=[p for p in nav if "mount('"+p+"'" not in js]
if missing: raise SystemExit('UI14_NAV_MISSING='+','.join(missing))
cmd=[sys.executable,'-m','unittest','src.ui.tests.test_ui14_full_console','-v']
# Running through discover is more reliable across Windows environments.
proc=subprocess.run([sys.executable,'-m','unittest','discover','-s','src/ui/tests','-p','test_ui14_full_console.py','-v'],cwd=root,text=True)
if proc.returncode: raise SystemExit(proc.returncode)
print('UI14_O46_FULL_CONSOLE_PASS')
print('UI14_NAV_PAGES_DESIGNED',len(nav))
print('UI14_SEMANTIC_MAPPING_FIX_INCLUDED')
print('UI14_GOVERNANCE_BOUNDARY_PRESERVED')
print('UI14_RESPONSIVE_SURFACES_INCLUDED')
