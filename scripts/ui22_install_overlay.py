from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
UI=ROOT/'src'/'ui'/'ui'
index=UI/'index.html'
js=index.read_text(encoding='utf-8')
css='src/ui/ui/ui22_console.css'; script='src/ui/ui/ui22_console.js'
if script not in js:
    marker='<script src="ux21_console.js?v=1.0.0"></script>'
    if marker in js:
        js=js.replace(marker, marker+f'\n  <link rel="stylesheet" href="{css}" />\n  <script src="{script}"></script>')
    else:
        needle='<script src="app.js?v=4.6.0"></script>'
        js=js.replace(needle, needle+f'\n  <link rel="stylesheet" href="{css}" />\n  <script src="{script}"></script>')
    index.write_text(js,encoding='utf-8')
print('UI22_OVERLAY_INSTALLED')
print('UI22_SINGLE_VISIBLE_PAGE_ENFORCEMENT_BOUND')
print('UI22_RECONCILIATION_LEAK_PREVENTED')
print('UI22_STATE_TEXT_TRIM_BOUND')
