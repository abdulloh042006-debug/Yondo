import json
import os
AD=os.environ.get('AD', '/path/to/ad')
s=open(f'{AD}/page.tpl.html').read()
s=s.replace('__FS__','file:///home/claude/fonttools/node_modules/@fontsource')
s=s.replace('__TIMELINE__',open(f'{AD}/timeline.json').read())
s=s.replace('__WORDMARK__',open(f'{AD}/wordmark.svgfrag').read())
s=s.replace('__SHOTS__',json.dumps({'uz':'file://'+AD+'/shots-yondo','ru':'file://'+AD+'/shots-yondo-ru'}))  # RU cut: Russian app screens
open(f'{AD}/page.html','w').write(s)
