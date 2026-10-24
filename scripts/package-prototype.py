"""Build a self-contained local HTML artifact from the editable prototype sources."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
dist = root / 'prototype' / 'dist'
html = (dist / 'index.html').read_text()
html = html.replace('<link rel="stylesheet" href="style.css">', '<style>' + (dist / 'style.css').read_text() + '</style>')
html = html.replace('<script src="framework.js"></script>', '<script>' + (dist / 'framework.js').read_text() + '</script>')
html = html.replace('<script src="public-snapshot.js"></script>', '<script>' + (dist / 'public-snapshot.js').read_text() + '</script>')
html = html.replace('<script src="research.js"></script>', '<script>' + (dist / 'research.js').read_text() + '</script>')
html = html.replace('<script src="retrieval.js"></script>', '<script>' + (dist / 'retrieval.js').read_text() + '</script>')
html = html.replace('<script src="app.js"></script>', '<script>' + (dist / 'app.js').read_text() + '</script>')
(root / 'prototype' / '观澜-可交互原型.html').write_text(html)
print('Created self-contained prototype HTML')
