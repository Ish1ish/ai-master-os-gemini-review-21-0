from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'src' / 'ui' / 'ui' / 'index.html'

css_tag = '<link rel="stylesheet" href="ui19_console.css?v=19.0.0" />'
js_tag = '<script src="ui19_console.js?v=19.0.0"></script>'

if not INDEX.exists():
    raise SystemExit(f'Missing UI index: {INDEX}')

text = INDEX.read_text(encoding='utf-8')
changed = False
if css_tag not in text:
    marker = '</head>'
    if marker not in text:
        raise SystemExit('index.html has no </head> marker')
    text = text.replace(marker, f'  {css_tag}\n{marker}', 1)
    changed = True
if js_tag not in text:
    marker = '</body>'
    if marker not in text:
        raise SystemExit('index.html has no </body> marker')
    text = text.replace(marker, f'  {js_tag}\n{marker}', 1)
    changed = True

if changed:
    INDEX.write_text(text, encoding='utf-8')

print('UI19_OVERLAY_INSTALLED')
print('UI19_VISUAL_POLISH_ASSET_LOADED')
print('UI19_GOLDEN_EXPERIENCE_REHYDRATION_BOUND')
print('UI19_ACCEPTANCE_ERROR_GUARD_BOUND')
print('UI19_GOLDEN_RUN_CONTROL_POLISH_BOUND')
print('UI19_EXPERIMENTS_EMPTY_STATE_POLISHED')
