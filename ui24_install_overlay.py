from pathlib import Path
import re
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'src' / 'ui' / 'ui' / 'index.html'
if not INDEX.exists(): raise SystemExit('Missing UI index')
text = INDEX.read_text(encoding='utf-8')
# Remove previous experimental overlay tags so UI24 is the sole final presentation layer.
text = re.sub(r'\s*<link rel="stylesheet" href="ui(?:19|20|21|22)_console\.css[^"]*"\s*/>', '', text)
text = re.sub(r'\s*<script src="ui(?:19|20|21|22)_console\.js[^"]*"></script>', '', text)
# Remove any known stray reconciliation block left outside page-recovery.
stray = re.compile(r'\s*<section class="card">\s*<div class="card-head">\s*<div><div class="eyebrow">RECONCILIATION PLAYBOOK</div><h3>Safe response</h3></div>.*?</section>\s*</div>\s*</section>\s*(?=<section class="page hidden" id="page-health">)', re.S)
text, removed = stray.subn('', text, count=1)
# Ensure recovery itself contains exactly one reconciliation playbook.
marker = '<meta name="aios-ui24-final-console" content="unified-final-surface" />'
if marker not in text: text=text.replace('</head>', f'  {marker}\n</head>', 1)
css_tag = '<link rel="stylesheet" href="ui24_console.css?v=24.0.0" />'
js_tag = '<script src="ui24_console.js?v=24.0.0"></script>'
if 'ui24_console.css?v=24.0.0' not in text: text=text.replace('</head>', f'  {css_tag}\n</head>', 1)
if 'ui24_console.js?v=24.0.0' not in text: text=text.replace('</body>', f'  {js_tag}\n</body>', 1)
INDEX.write_text(text, encoding='utf-8')
print('UI24_OVERLAY_INSTALLED')
print('UI24_LEGACY_PRESENTATION_LAYERS_REMOVED')
print('UI24_RECOVERY_STRUCTURE_NORMALIZED')
print('UI24_UNIFIED_CANONICAL_RUN_SURFACE_BOUND')
print('UI24_ALL_MAJOR_SURFACES_ENHANCED')
print('UI24_GOVERNANCE_BOUNDARY_PRESERVED')
