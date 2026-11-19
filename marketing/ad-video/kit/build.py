"""Build an ad page from a template that uses the kit.

Usage: python3 kit/build.py <template.html> <out.html>
Env: FONTS = @fontsource folder (with manrope/ and space-grotesk/), SHOTS = folder of app captures / AI clips (optional),
CTA = end-card call to action (default "[ CTA ]": a visible placeholder until the owner picks «Tez kunda» or a link).
REEL_LANG = uz (default) or ru.
Placeholders: {{FONTS}} {{SHOTS}} {{KIT_JS}} {{WORDMARK_INLINE}} {{CTA}} {{LANG}} (the template defines `const WORDMARK` from it).
"""
import os
import pathlib
import sys

here = pathlib.Path(__file__).parent
src, dst = map(pathlib.Path, sys.argv[1:3])
html = src.read_text(encoding='utf-8')
wm = (here.parent / 'wordmark.svgfrag').read_text(encoding='utf-8').strip()   # outlined wordmark path (never retyped)
kit = (here / 'kit.js').read_text(encoding='utf-8')
assert '`' not in wm
cta = os.environ.get('CTA', '[ CTA ]')
html = (html.replace('{{KIT_JS}}', kit).replace('{{CTA}}', cta).replace('{{WORDMARK_INLINE}}', wm)
        .replace('{{LANG}}', os.environ.get('REEL_LANG', 'uz'))
        .replace('{{FONTS}}', 'file://' + os.environ.get('FONTS', ''))
        .replace('{{SHOTS}}', 'file://' + os.environ.get('SHOTS', '')))
assert '{{' not in html, 'unfilled placeholder'
dst.write_text(html, encoding='utf-8')
print('built', dst)
