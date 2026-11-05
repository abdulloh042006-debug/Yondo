import json
import os
AD=os.environ.get('AD', '/path/to/ad')
s=open(f'{AD}/page.tpl.html').read()
s=s.replace('__FS__','file:///home/claude/fonttools/node_modules/@fontsource')
s=s.replace('__TIMELINE__',open(f'{AD}/timeline.json').read())
s=s.replace('__WORDMARK__',open(f'{AD}/wordmark.svgfrag').read())
s=s.replace('__SHOTS__',json.dumps({'uz':'file://'+AD+'/shots-yondo','ru':'file://'+AD+'/shots-yondo-ru'}))
import os
def _box(d, n):
    f = f'{AD}/{d}/{n}-profile.json'
    return json.load(open(f)) if os.path.exists(f) else None
pb = {lang: {'m': _box(d, 'm'), 'd': _box(d, 'd')} for lang, d in (('uz', 'shots-yondo'), ('ru', 'shots-yondo-ru'))}
s = s.replace('__PHOTOBOX__', json.dumps(pb))
_mad = os.environ.get('MADINA_SVG', '/home/claude/yondo/marketing/ad-video/photos/madina-anim.svg.txt')
s = s.replace('__MADINA__', open(_mad).read().replace('`', '') if os.path.exists(_mad) else '')
open(f'{AD}/page.html','w').write(s)
