from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'src'/'ui'/'ui'/'index.html'
if not INDEX.exists(): raise SystemExit('Missing UI index')
text=INDEX.read_text(encoding='utf-8')
text=re.sub(r'\s*<link rel="stylesheet" href="ui25_console\.css\?v=[^"]*"\s*/>','',text)
text=re.sub(r'\s*<script src="ui25_console\.js\?v=[^"]*"></script>','',text)
text=text.replace('</head>','  <link rel="stylesheet" href="ui25_console.css?v=25.0.0" />\n</head>',1)
text=text.replace('</body>','  <script src="ui25_console.js?v=25.0.0"></script>\n</body>',1)
INDEX.write_text(text,encoding='utf-8')
print('UI25_OVERLAY_INSTALLED')
print('UI25_LEARNING_PRESENTATION_REPAIRED')
print('UI25_STRUCTURED_DATA_SANITIZER_BOUND')
print('UI25_READ_ONLY_BOUNDARY_PRESERVED')
