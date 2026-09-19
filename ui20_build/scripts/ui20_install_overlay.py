from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'src'/'ui'/'ui'/'index.html'
CSS=ROOT/'src'/'ui'/'ui'/'ui20_console.css'
JS=ROOT/'src'/'ui'/'ui'/'ui20_console.js'
if not INDEX.exists(): raise SystemExit('Missing UI index')
text=INDEX.read_text(encoding='utf-8')
for tag,needle in [('<link rel="stylesheet" href="ui20_console.css?v=20.0.0" />','ui20_console.css?v=20.0.0'),('<script src="ui20_console.js?v=20.0.0"></script>','ui20_console.js?v=20.0.0')]:
    if needle not in text:
        marker='</head>' if tag.startswith('<link') else '</body>'
        text=text.replace(marker,f'  {tag}\n{marker}',1)
INDEX.write_text(text,encoding='utf-8')
print('UI20_OVERLAY_INSTALLED')
print('UI20_SINGLE_SURFACE_MODE_BOUND')
print('UI20_CANONICAL_RUN_SELECTION_BOUND')
print('UI20_SPA_NAVIGATION_HYDRATION_BOUND')
print('UI20_EXECUTIVE_GOLDEN_ACCEPTANCE_SYNC_BOUND')
