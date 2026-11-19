"""Turn a Google Flow prompt pack (Markdown) into one phone-friendly HTML file with copy buttons.

Usage: python3 flowpack_html.py flow-pack-sample-reja.md flow-pack-sample-reja.html "Yondo Flow namuna"
Handles only what the packs use: # headings, paragraphs, - / 1. lists, - [ ] checks, tables, ``` code, **bold**, `code`.
"""
import html
import re
import sys

CSS = """
:root{--ink:#111111;--paper:#F5F2EC;--carrot:#E8501A;--line:color-mix(in srgb,var(--ink) 16%,var(--paper));--bg:var(--paper);--fg:var(--ink);--card:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:var(--ink);--fg:var(--paper);--card:#1c1c1c;--line:color-mix(in srgb,var(--paper) 18%,var(--ink));color-scheme:dark}}
:root[data-theme="dark"]{--bg:var(--ink);--fg:var(--paper);--card:#1c1c1c;--line:color-mix(in srgb,var(--paper) 18%,var(--ink));color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:760px;margin:0 auto;padding-block:20px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}h1{font-size:1.5rem;line-height:1.25;border-bottom:4px solid var(--carrot);padding-bottom:10px}
h2{font-size:1.2rem;margin-top:2.2em}h3{font-size:1.05rem;margin-top:1.8em;padding:8px 12px;background:var(--card);border-left:4px solid var(--carrot);border-radius:6px}
.tw{overflow-x:auto;margin:12px 0}table{border-collapse:collapse;font-size:.88rem;min-width:100%}th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:var(--card)}pre{position:relative;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:44px 12px 12px;white-space:pre-wrap;word-break:break-word;font-size:.85rem}
button.cp{position:absolute;top:8px;right:8px;font:600 .85rem system-ui;padding:6px 12px;border-radius:999px;border:0;background:var(--fg);color:var(--bg);cursor:pointer}
code{font-size:.9em}li{margin:4px 0}.chk{list-style:none;padding-left:4px}
"""

JS = """document.querySelectorAll('pre').forEach(p=>{const b=document.createElement('button');b.className='cp';b.textContent='Nusxa olish';
b.onclick=async()=>{const t=p.querySelector('code').innerText;try{await navigator.clipboard.writeText(t);b.textContent='Nusxalandi ✓'}catch(e){
const r=document.createRange();r.selectNodeContents(p.querySelector('code'));const s=getSelection();s.removeAllRanges();s.addRange(r);b.textContent='Belgilandi'}
setTimeout(()=>b.textContent='Nusxa olish',1600)};p.prepend(b)});"""


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)


def convert(md):
    out, lines, i = [], md.split('\n'), 0
    title = 'Flow prompt pack'
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('```'):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                buf.append(lines[i])
                i += 1
            out.append('<pre><code>' + html.escape('\n'.join(buf)) + '</code></pre>')
        elif m := re.match(r'(#{1,3}) (.*)', ln):
            n = len(m.group(1))
            if n == 1:
                title = m.group(2)
            out.append(f'<h{n}>{inline(m.group(2))}</h{n}>')
        elif ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'-+', c) for c in cells):
                    rows.append(cells)
                i += 1
            i -= 1
            head = ''.join(f'<th>{inline(c)}</th>' for c in rows[0])
            body = ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in rows[1:])
            out.append(f'<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
        elif re.match(r'(- |\d+\. )', ln):
            ordered = bool(re.match(r'\d+\. ', ln))
            items = []
            while i < len(lines) and (re.match(r'(- |\d+\. )', lines[i]) or (items and lines[i].startswith('   '))):
                if lines[i].startswith('   '):
                    items[-1] += ' ' + lines[i].strip()
                else:
                    items.append(re.sub(r'^(- |\d+\. )', '', lines[i]))
                i += 1
            i -= 1
            chk = all(it.startswith('[ ]') for it in items)
            tag = 'ol' if ordered else 'ul'
            lis = ''.join('<li>' + ('☐ ' + inline(it[3:].strip()) if chk else inline(it)) + '</li>' for it in items)
            out.append(f'<{tag}{" class=chk" if chk else ""}>{lis}</{tag}>')
        elif ln.strip():
            buf = [ln]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r'(#|\||- |\d+\. |```)', lines[i + 1]):
                i += 1
                buf.append(lines[i])
            out.append('<p>' + inline(' '.join(s.strip() for s in buf)) + '</p>')
        i += 1
    return title, '\n'.join(out)


def main(src, dst, short_title=None):
    with open(src, encoding='utf-8') as f:
        title, body = convert(f.read())
    page = (f'<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="claude:viewport-fit-sides" content="cover">'
            f'<title>{html.escape(short_title or title)}</title><style>{CSS}</style></head><body><main>{body}</main><script>{JS}</script></body></html>\n')
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(page)


if __name__ == '__main__':
    main(*sys.argv[1:4])
