"""Reel 1 soundtrack: original synthesis only (numpy), 48 kHz stereo, no samples, no voice.
Music 120 BPM: A minor (loneliness, 0-8 s) -> C major groove (possibility, 9-22 s) -> warm pad (22-29 s) -> logo chord.
SFX cues are listed in CUES and written to cues.json so audio-ears can check that they land on the cuts.
Usage: OUT=<dir> python3 audio.py   ->  <dir>/mix.wav (pre-loudnorm), <dir>/cues.json"""
import json, os, wave
import numpy as np
SR = 48000; T = 34.0; N = int(SR * T)
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)
def at(t): return int(t * SR)
def add(sig, t, g=1.0, pan=0.0):
    i = at(t); j = min(N, i + len(sig)); s = sig[: j - i] * g
    L[i:j] += s * np.sqrt((1 - pan) / 2) * 1.414; R[i:j] += s * np.sqrt((1 + pan) / 2) * 1.414
def env(n, a=.005, d=None, k=6.0):
    x = np.arange(n) / SR; e = 1 - np.exp(-x / max(a, 1e-4)); return e * np.exp(-x * k) if d is None else e
def lp(x, fc):          # one-pole low-pass, fc scalar or per-sample array
    fc = np.broadcast_to(np.asarray(fc, float), x.shape); a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); s = 0.0
    for i in range(len(x)): s = (1 - a[i]) * x[i] + a[i] * s; y[i] = s
    return y
def hp(x, fc): return x - lp(x, fc)
def note(f): return 440 * 2 ** ((f - 69) / 12)
def tone(f, dur, k=3.0, harm=(1, .5, .25, .12)):
    n = at(dur); x = np.arange(n) / SR
    return sum(h * np.sin(2 * np.pi * f * (i + 1) * x) * np.exp(-x * k * (1 + i * .7)) for i, h in enumerate(harm)) * env(n, .004, 1)
def pad(fs, dur, att=.6, cut=1400):
    n = at(dur); x = np.arange(n) / SR; s = np.zeros(n)
    for f in fs:
        for dt in (-.25, .25): s += ((x * f * (1 + dt / 100)) % 1 * 2 - 1) * .15
    s = lp(s, cut); e = np.minimum(1, x / att) * np.minimum(1, (dur - x) / .4); return s * e
def kick(g=1):
    n = at(.35); x = np.arange(n) / SR; f = 45 + 95 * np.exp(-x * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 9) * g
def hat(): n = at(.05); return hp(rng.standard_normal(n), 7000) * np.exp(-np.arange(n) / SR * 90) * .25
def clap(): n = at(.18); return lp(hp(rng.standard_normal(n), 1200), 5000) * np.exp(-np.arange(n) / SR * 28) * .45
def click(f=2200): n = at(.03); x = np.arange(n) / SR; return np.sin(2 * np.pi * f * x) * np.exp(-x * 220) * .6 + hp(rng.standard_normal(n), 3000) * np.exp(-x * 400) * .25
def tick(): n = at(.025); x = np.arange(n) / SR; return hp(rng.standard_normal(n), 2500) * np.exp(-x * 500) * .5 + np.sin(2 * np.pi * 3200 * x) * np.exp(-x * 300) * .3
def whoosh(dur=.45, f0=300, f1=4000):
    n = at(dur); x = np.linspace(0, 1, n); fc = f0 * (f1 / f0) ** x
    return lp(rng.standard_normal(n), fc) * np.sin(np.pi * x) ** 1.5 * .9
def riser(dur):
    n = at(dur); x = np.linspace(0, 1, n); fc = 200 * 40 ** x
    return (lp(rng.standard_normal(n), fc) * .5 + np.sin(2 * np.pi * np.cumsum(180 + 500 * x ** 2) / SR) * .15) * x ** 2
def impact(g=1):
    n = at(1.6); x = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-x * 14)) / SR) * np.exp(-x * 2.6)
    return (sub * .55 + lp(rng.standard_normal(n), 1800) * np.exp(-x * 14) * .7) * g
def chime(f=1318.5): return tone(f, 1.6, 2.2, (1, .3, .1)) * .35 + tone(f * 1.5, 1.6, 2.6, (1, .2)) * .18
def sparkle(dur):
    out = np.zeros(at(dur))
    for k in range(18):
        s = tone(note(84 + int(rng.integers(0, 12))), .25, 14, (1, .2)) * .12; i = int(rng.integers(0, max(1, len(out) - len(s)))); out[i:i + len(s)] += s
    return out
CUES = []
def cue(t, name, sig, g=1.0, pan=0.0): add(sig, t, g, pan); CUES.append({'t': round(t, 3), 'sfx': name})

# ---------- music ----------
B = .5  # beat
# 0-3: drone + city ambience
add(pad([note(45), note(52)], 2.2, .3, 600), 0, .55)
amb = lp(rng.standard_normal(at(1.3)), 700) * np.minimum(1, np.arange(at(1.3)) / SR / .2) * np.minimum(1, (1.3 - np.arange(at(1.3)) / SR) / .3)
add(amb, 1.95, .35)
# 3-8: lonely piano, A minor, sparse
for t0, m in [(3.0, 57), (3.5, 64), (4.0, 60), (4.5, 64), (5.0, 55), (5.5, 62), (6.0, 57), (6.75, 60), (7.25, 64)]:
    add(tone(note(m), 1.2, 2.5), t0, .32, -.2)
add(pad([note(45), note(57), note(60), note(64)], 5.0, 1.0, 900), 3.0, .35)
# 9-22: C - G - Am - F groove
prog = [[48, 55, 60, 64], [43, 55, 59, 62], [45, 57, 60, 64], [41, 57, 60, 65]]
t = 9.0; bar = 0
while t < 22.0 - 1e-6:
    ch = prog[bar % 4]; dur = min(2.0, 22.0 - t)
    add(pad([note(m) for m in ch[1:]], dur, .15 if t > 9.5 else .8, 2200), t, .32)
    for b in range(4):
        tb = t + b * B
        if tb >= 22: break
        if tb >= 13.0 or b % 2 == 0: add(kick(), tb, .5)
        if tb >= 13.0 and b % 2 == 1: add(clap(), tb, .5, .1)
        add(tone(note(ch[0]), .45, 5, (1, .6, .3)), tb, .28)          # bass
        if tb >= 13.0:
            add(hat(), tb + B / 2, .6, .3)
            add(tone(note(ch[1 + (b % 3)] + 12), .3, 8, (1, .3)), tb + B / 2, .14, -.3)  # pluck arpeggio
    t += 2.0; bar += 1
# 22-29: warm, no drums; rising arpeggio
for i, ch in enumerate([[45, 60, 64, 69], [41, 57, 60, 65], [48, 60, 64, 67], [43, 59, 62, 67]]):
    t0 = 22 + i * 1.75; add(pad([note(m) for m in ch], 1.9, .5, 1600 + i * 300), t0, .42)
    add(tone(note(ch[0]), 1.8, 1.2, (1, .5, .2)), t0, .25)
    for k in range(7): add(tone(note(ch[1 + k % 3] + 12 * (k // 3)), .5, 4, (1, .25)), t0 + k * .25, .12 + i * .02, (k % 2 - .5) * .6)
# 29-34: logo chord, ringing
add(pad([note(m) for m in [48, 55, 60, 64, 67]], 5.0, .4, 2400), 29.0, .45)
add(tone(note(48), 4.5, .6, (1, .5, .25)), 30.2, .3)

# ---------- SFX (times = page.tpl.html cues) ----------
for k in range(int(1.95 * 6)): cue(k / 6, 'clock tick', tick(), .5 if k * 1 / 6 < 1.25 else .7)
for i in range(5): cue(.5 + i * .06, 'digit pop', click(900 + i * 180), .45, (i - 2) * .3)
cue(.9, 'riser (dive)', riser(.98), .8)
cue(1.95, 'bass hit (carrot flood -> city)', impact(), 1.0)
for t0 in (3.0, 4.0, 5.0): cue(t0 - .02, 'whoosh (cut)', whoosh(.32, 400, 5000), .7, .4)
for k in range(6): cue(5.0 + k / 6, 'clock tick', tick(), .6)
cue(6.0, 'impact soft (words in)', impact(.45), 1.0)
cue(6.6, 'sparkle (letters dissolve)', sparkle(.8), 1.0)
cue(7.35, 'ui pop (typing bubble)', click(1400), .8)
for k in range(5): cue(7.45 + k * .1, 'typing', tick(), .35)
cue(8.0, 'whoosh (zoom into the dots)', whoosh(.6, 200, 3000), .8)
for i in range(3): cue(8.75 + i * .04, 'ping (dots fly)', chime(note(76 + i * 3)), .9, (i - 1) * .6)
for t0 in (9.25, 10.5, 11.75):
    cue(t0, 'pop (dot opens)', click(1100), 1.0); add(kick(.5), t0, .6)
    cue(t0, 'transition swell (iris)', whoosh(.55, 300, 6000), .6); cue(t0 + .05, 'chime', chime(note(79)), .7)
cue(12.4, 'riser', riser(.6), .7)
cue(13.0, 'bass hit (product)', impact(.8), 1.0)
for t0 in (14.0, 14.9, 16.3, 19.4, 20.85): cue(t0, 'swipe (screen change)', whoosh(.22, 1200, 7000), .45, .2)
for t0 in (13.55, 15.15, 18.2, 21.05): cue(t0, 'ui click (element lifts)', click(), .8)
for t0 in (16.45, 16.6, 17.35, 17.5): cue(t0, 'card flip', click(1600), .6, .4 if t0 < 17 else -.4)
cue(20.35, 'tap', click(2600), .9)
cue(21.05, 'success chime', chime(note(84)), .8)
cue(21.95, 'whoosh (phone -> sun)', whoosh(.5, 3000, 200), .8)
cue(22.0, 'bass hit (ending)', impact(.7), 1.0)
cue(28.4, 'riser', riser(.6), .7)
cue(29.0, 'whoosh (pieces fly in)', whoosh(1.1, 200, 5000), .7)
cue(30.2, 'bass hit (logo assembled)', impact(1.0), 1.0)
cue(31.1, 'whoosh (lockup)', whoosh(.5, 800, 6000), .6)
cue(31.4, 'shimmer (wordmark)', sparkle(.8), .8)
cue(32.1, 'soft hit (tagline)', impact(.35), 1.0)
cue(32.1, 'chime', chime(note(88)), .6)

# fade-out last 1.2 s, soft limit
fo = np.ones(N); n = at(1.2); fo[-n:] = np.linspace(1, 0, n) ** 2
mix = np.stack([L, R], 1) * fo[:, None]
mix = np.tanh(mix / (np.abs(mix).max() * .9) * 1.2) * .7
out = os.environ.get('OUT', '.')
with wave.open(f'{out}/mix.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
json.dump(CUES, open(f'{out}/cues.json', 'w'), indent=0)
print('mix.wav', len(CUES), 'cues')
