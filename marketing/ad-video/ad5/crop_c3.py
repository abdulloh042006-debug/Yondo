"""Crop the C3 captures so no file used in the edit contains a price.

Usage: python3 ad5/crop_c3.py <shots dir>   (the folder written by ad5/capture_c3.mjs)
card-crop.png  = the card from its top to 30 px under the category chips (stats row and price line are below);
place-crop.png = label «Uchrashuv joyi» + field + the app's hint (service select and price estimate are outside).
"""
import json
import pathlib
import subprocess
import sys

d = pathlib.Path(sys.argv[1])
W, H = 975, 2110                       # 390x844 css px at deviceScaleFactor 2.5


def crop(src, w, h, x, y, dst):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(d / src), '-vf', f'crop={w}:{h}:{x}:{y}', str(d / dst)], check=True)


c = json.loads((d / 'card.json').read_text())
x, y, w = round(c['card']['x'] * W), round(c['card']['y'] * H), round(c['card']['w'] * W)
bottom = round((c['tags']['y'] + c['tags']['h']) * H) + 30
assert bottom < round(c['price']['y'] * H), 'crop would reach the price line'
crop('card.png', w, bottom - y, x, y, 'card-crop.png')

f = json.loads((d / 'place-field.json').read_text())
y0 = round(f['label']['y'] * H) - 28
y1 = round((f['hint']['y'] + f['hint']['h']) * H) + 24
x0 = round(f['label']['x'] * W) - 28
crop('place.png', W - 2 * x0, y1 - y0, x0, y0, 'place-crop.png')
print('card', w, bottom - y, '| place', W - 2 * x0, y1 - y0, '| tags y in card crop', round(c['tags']['y'] * H) - y)
