from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'src' / 'ui' / 'ui' / 'index.html'
if not INDEX.exists():
    raise SystemExit('Missing UI index')
text = INDEX.read_text(encoding='utf-8')
css_tag = '<link rel="stylesheet" href="ui21_console.css?v=21.0.0" />'
js_tag = '<script src="ui21_console.js?v=21.0.0"></script>'
if 'ui21_console.css?v=21.0.0' not in text:
    text = text.replace('</head>', f'  {css_tag}\n</head>', 1)
if 'ui21_console.js?v=21.0.0' not in text:
    text = text.replace('</body>', f'  {js_tag}\n</body>', 1)
INDEX.write_text(text, encoding='utf-8')
print('UI21_OVERLAY_INSTALLED')
print('UI21_SINGLE_PAGE_SURFACE_BOUND')
print('UI21_DUPLICATE_SURFACES_SUPPRESSED')
print('UI21_CANONICAL_RUN_BOUND')
print('UI21_PROXY_ACTIONS_BOUND')
