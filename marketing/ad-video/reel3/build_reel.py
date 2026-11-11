"""Build reel 3 page.html from page.tpl.html.
Env: SHOTS = folder with the apps/web captures (capture.mjs + capture_list.mjs), FONTS = @fontsource folder,
OUT = output folder (default: SHOTS/..)."""
import os, pathlib
here = pathlib.Path(__file__).parent
shots = os.environ['SHOTS']
fonts = os.environ.get('FONTS', '/home/claude/fonttools/node_modules/@fontsource')
out = pathlib.Path(os.environ.get('OUT', pathlib.Path(shots).parent))
wm = (here.parent / 'wordmark.svgfrag').read_text().strip()   # outlined wordmark path (never retyped)
html = (here / 'page.tpl.html').read_text()
html = html.replace('{{SHOTS}}', 'file://' + shots).replace('{{FONTS}}', 'file://' + fonts).replace('{{WORDMARK}}', wm)
assert '{{' not in html
(out / 'page.html').write_text(html)
print('page.html ->', out)
