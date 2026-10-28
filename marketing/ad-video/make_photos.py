"""Illustrated profile pictures for the promo-video seed (NOT photos of real people).
Brand palette only: ink #111111, paper #F5F2EC / white, carrot #E8501A and its tints mixed with paper.
Writes SVGs to photos/*.svg; render_photos.mjs turns them into 1080x1350 JPEGs."""
import os

OUT = os.path.join(os.path.dirname(__file__), 'photos')
INK, PAPER, CAR = '#111111', '#F5F2EC', '#E8501A'
SKIN, SKIN2, BLUSH = '#F2CDB9', '#E6AE93', '#E8501A'
W, H = 1080, 1350


def svg(body, bg):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="{bg}"/>{body}</svg>'


def face(cx=540, cy=700, smile=True, glasses=False):
    s = f'<ellipse cx="{cx - 178}" cy="{cy + 20}" rx="26" ry="40" fill="{SKIN2}"/><ellipse cx="{cx + 178}" cy="{cy + 20}" rx="26" ry="40" fill="{SKIN2}"/>'
    s += f'<ellipse cx="{cx}" cy="{cy}" rx="176" ry="214" fill="{SKIN}"/>'
    st = f'fill="none" stroke="{INK}" stroke-width="9" stroke-linecap="round"'
    s += f'<path d="M{cx - 104} {cy - 46}q34 -22 68 -4M{cx + 36} {cy - 50}q34 -18 68 4" {st}/>'  # brows
    if smile:
        s += f'<path d="M{cx - 96} {cy + 6}q26 -22 52 0M{cx + 44} {cy + 6}q26 -22 52 0" {st}/>'  # happy closed eyes
    else:
        s += f'<circle cx="{cx - 70}" cy="{cy + 4}" r="11" fill="{INK}"/><circle cx="{cx + 70}" cy="{cy + 4}" r="11" fill="{INK}"/>'
    s += f'<path d="M{cx + 4} {cy + 30}q-14 46 -2 60q10 6 22 0" fill="none" stroke="{SKIN2}" stroke-width="9" stroke-linecap="round"/>'  # nose
    s += f'<path d="M{cx - 52} {cy + 120}q52 42 104 0" {st}/>'  # smile
    s += f'<circle cx="{cx - 112}" cy="{cy + 92}" r="30" fill="{BLUSH}" opacity=".16"/><circle cx="{cx + 112}" cy="{cy + 92}" r="30" fill="{BLUSH}" opacity=".16"/>'
    if glasses:
        g = f'fill="none" stroke="{INK}" stroke-width="10"'
        s += f'<rect x="{cx - 132}" y="{cy - 30}" width="104" height="78" rx="30" {g}/><rect x="{cx + 28}" y="{cy - 30}" width="104" height="78" rx="30" {g}/><path d="M{cx - 28} {cy}h56" {g}/>'
    return s


def body(color, collar=None, cx=540):
    s = f'<path d="M{cx - 70} 850h140v190q-70 40 -140 0z" fill="{SKIN2}"/>'  # neck
    s += f'<path d="M150 {H}C170 1110 330 1010 {cx} 1000C750 1010 910 1110 930 {H}Z" fill="{color}"/>'
    if collar:
        s += f'<path d="M{cx - 110} 1004q110 90 220 0" fill="none" stroke="{collar}" stroke-width="14" stroke-linecap="round"/>'
    return s


def skyline(color, base, op):
    s, x, i = '', 20, 0
    hs = [160, 240, 120, 300, 190, 260, 140, 220, 180, 280]
    while x < W:
        w = 70 + (i * 37) % 60; h = hs[i % len(hs)]
        s += f'<rect x="{x}" y="{base - h}" width="{w}" height="{h}" fill="none" stroke="{color}" stroke-width="5"/>'
        x += w + 18; i += 1
    s += f'<path d="M{W * .78} {base}l18 -330l18 330M{W * .78 + 6} {base - 210}h24" fill="none" stroke="{color}" stroke-width="5"/>'
    return f'<g opacity="{op}">{s}</g>'


def madina():
    b = f'<circle cx="540" cy="660" r="430" fill="{CAR}"/>' + skyline(PAPER, 1000, .35)
    b += f'<path d="M330 640C320 380 430 300 560 300C700 300 790 400 770 640L800 1060Q540 1120 290 1060Z" fill="{INK}"/>'  # long hair behind
    b += body(INK, collar=CAR) + face()
    b += f'<path d="M370 620C360 420 470 360 560 362C680 366 740 450 724 600C690 500 600 470 500 520C450 545 400 590 370 620Z" fill="{INK}"/>'  # fringe
    b += f'<circle cx="362" cy="770" r="13" fill="{PAPER}"/>'
    return svg(b, PAPER)


def jasur():
    b = f'<circle cx="540" cy="660" r="430" fill="{CAR}"/><circle cx="900" cy="230" r="60" fill="{PAPER}"/>' + skyline(PAPER, 1000, .3)
    b += body(PAPER, collar=CAR) + face(glasses=True)
    b += f'<path d="M370 600C350 420 450 350 560 350C680 352 742 430 716 600C700 520 650 490 600 500C540 470 440 500 370 600Z" fill="{INK}"/>'
    b += f'<path d="M420 860q120 70 240 0" fill="none" stroke="{SKIN2}" stroke-width="10" stroke-linecap="round" opacity=".7"/>'
    return svg(b, INK)


def sevara():
    b = f'<rect x="0" y="0" width="{W}" height="{H}" fill="#F3DCD0"/><circle cx="540" cy="660" r="430" fill="{PAPER}"/>'
    b += f'<circle cx="540" cy="390" r="110" fill="{INK}"/>' + body(CAR, collar=PAPER) + face()
    b += f'<path d="M366 640C350 440 460 380 560 380C690 384 744 470 716 640C690 540 610 500 540 512C460 520 400 580 366 640Z" fill="{INK}"/>'
    return svg(b, PAPER)


def coffee():
    st = f'fill="none" stroke="{INK}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"'
    b = skyline(INK, 760, .25) + f'<rect x="0" y="760" width="{W}" height="{H - 760}" fill="#F3DCD0"/>'
    b += f'<path d="M140 900H940" {st}/><path d="M220 900v320M860 900v320" {st}/>'
    for cx, c in ((420, CAR), (660, INK)):
        b += f'<path d="M{cx - 80} 760h160v70a80 70 0 0 1 -160 0z" fill="{c}"/><path d="M{cx + 80} 780h22a30 30 0 0 1 0 60h-22" {st}/>'
        b += f'<path d="M{cx - 30} 700q-14 -30 0 -60M{cx + 10} 700q-14 -30 0 -60" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round" opacity=".5"/>'
    b += f'<circle cx="540" cy="300" r="120" fill="{CAR}" opacity=".9"/>'
    return svg(b, PAPER)


def books():
    st = f'fill="none" stroke="{PAPER}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"'
    b = ''
    for i, (h, c) in enumerate(((300, CAR), (260, PAPER), (340, '#F3DCD0'), (220, CAR))):
        x = 260 + i * 120; b += f'<rect x="{x}" y="{1100 - h}" width="96" height="{h}" rx="10" fill="{c}"/>'
    b += f'<path d="M200 1100H880" {st}/>'
    b += f'<path d="M180 260h300v190H300l-60 60v-60h-60z" fill="{CAR}"/><text x="330" y="385" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="700" font-size="110" fill="{PAPER}">Aa</text>'
    b += f'<path d="M600 420h300v190H840v60l-60 -60H600z" fill="{PAPER}"/><text x="750" y="545" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="700" font-size="110" fill="{INK}">Аб</text>'
    return svg(b, INK)


def madina_anim():
    """Same picture as madina-1, split into groups the video animates: #m-head (fringe + face) and #m-arm / #m-hand (wave)."""
    b = f'<circle cx="540" cy="660" r="430" fill="{CAR}"/>' + skyline(PAPER, 1000, .35)
    b += f'<path d="M330 640C320 380 430 300 560 300C700 300 790 400 770 640L800 1060Q540 1120 290 1060Z" fill="{INK}"/>'
    b += body(INK, collar=CAR)
    b += '<g id="m-head">' + face()
    b += f'<path d="M370 620C360 420 470 360 560 362C680 366 740 450 724 600C690 500 600 470 500 520C450 545 400 590 370 620Z" fill="{INK}"/>'
    b += f'<circle cx="362" cy="770" r="13" fill="{PAPER}"/></g>'
    # raised hand (viewer's right): sleeve + palm + fingers; #m-hand rotates around the wrist (850, 905)
    arm = f'<path d="M905 1360C900 1180 880 1050 852 930" fill="none" stroke="{INK}" stroke-width="96" stroke-linecap="round"/>'
    hand = (f'<ellipse cx="850" cy="850" rx="50" ry="58" fill="{SKIN}"/>'
            + ''.join(f'<rect x="{x}" y="{y}" width="24" height="{h}" rx="12" fill="{SKIN}"/>' for x, y, h in ((806, 760, 70), (834, 746, 80), (862, 750, 76), (890, 768, 64)))
            + f'<rect x="782" y="830" width="24" height="56" rx="12" fill="{SKIN}" transform="rotate(-38 794 858)"/>')
    b += f'<g id="m-arm">{arm}<g id="m-hand"><g transform="translate(850 905) scale(1.4) translate(-850 -905)">{hand}</g></g></g>'
    return svg(b, PAPER)


os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'madina-anim.svg.txt'), 'w').write(madina_anim())  # embedded by build_page.py (not uploaded)
for name, fn in (('madina-1', madina), ('madina-2', coffee), ('jasur-1', jasur), ('jasur-2', books), ('sevara-1', sevara)):
    open(os.path.join(OUT, name + '.svg'), 'w').write(fn())
print('svgs', len(os.listdir(OUT)))
