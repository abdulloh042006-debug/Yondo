"""Reel 2 soundtrack: original synthesis only (numpy), 48 kHz stereo, no samples, no voice.
Energetic 120 BPM in C major from the first second (motion, many possibilities); every stitch gets a whoosh/hit on the cut.
Usage: OUT=<dir> python3 audio.py  ->  <dir>/mix.wav (pre-loudnorm), <dir>/cues.json"""
import json, os, wave
import numpy as np
SR = 48000; T = 30.0; N = int(SR * T)
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

# ---------- music: drums from 0, build, drop at 7 (kinetic words), groove 13-21, swell 21-27, chord 27-30 ----------
B = .5
prog = [[48, 55, 60, 64], [45, 57, 60, 64], [41, 57, 60, 65], [43, 55, 59, 62]]      # C Am F G
t = 0.0; bar = 0
while t < 27.0 - 1e-6:
    ch = prog[bar % 4]; dur = min(2.0, 27.0 - t)
    add(pad([note(m) for m in ch[1:]], dur, .1, 1800 + (600 if t >= 13 else 0)), t, .26)
    for b in range(4):
        tb = t + b * B
        if tb >= 27: break
        drums = not (21.0 <= tb < 23.0)                 # breakdown while the objects orbit
        if drums: add(kick(), tb, .5)
        if drums and b % 2 == 1 and tb >= 3: add(clap(), tb, .45, .1)
        if tb >= 7: add(hat(), tb + B / 2, .55, .3); add(hat(), tb + B / 4, .25, -.3)
        add(tone(note(ch[0]), .45, 5, (1, .6, .3)), tb, .26)
        add(tone(note(ch[1 + b % 3] + 12), .25, 9, (1, .3)), tb + B / 2, .12, -.3)
        if tb >= 13: add(tone(note(ch[1 + (b + 1) % 3] + 24), .2, 10, (1, .2)), tb + B * .75, .07, .4)
    t += 2.0; bar += 1
add(pad([note(m) for m in [48, 55, 60, 64, 67]], 3.0, .2, 2600), 27.0, .45)
add(tone(note(48), 3.0, .8, (1, .5, .25)), 27.0, .3)

# ---------- SFX (times = page.tpl.html cues) ----------
cue(0.0, 'whoosh (ball comes at the camera)', whoosh(1.0, 200, 5000), .8)
cue(1.0, 'bass hit (ball covers the screen)', impact(1.0), 1.0)
cue(1.0, 'whoosh (ball passes)', whoosh(.4, 4000, 300), .6)
cue(1.7, 'chime (sun)', chime(note(84)), .7)
cue(3.0, 'whoosh (tilt down)', whoosh(.3, 500, 5000), .6)
cue(3.3, 'cup set down (knock)', click(700), 1.0); add(kick(.6), 3.3, .5)
for t0 in (3.75, 4.6, 5.75): cue(t0, 'transition (match cut)', whoosh(.4, 400, 6000), .6); cue(t0, 'pop', click(1300), .8)
for k in range(10): cue(5.0 + k * .07, 'wheel tick', tick(), .35, .3)
for k in range(8): cue(6.15 + k * .1, 'clock tick', tick(), .5)
cue(7.0, 'bass hit (SUHBAT)', impact(.8), 1.0)
for i in range(6): cue(7.7 + i * .06, 'bubble pop', click(900 + i * 150), .6, (i % 2 - .5))
for k in range(5): cue(8.45 + k * .1, 'typing', tick(), .35)
cue(9.0, 'whoosh (SAYR)', whoosh(.4, 300, 5000), .7)
cue(9.55, 'whoosh (letters lie on the road)', whoosh(.7, 5000, 300), .6)
cue(11.0, 'bass hit (SHAHAR)', impact(.7), 1.0)
cue(11.6, 'shatter', sparkle(.5), 1.0)
cue(12.5, 'lock (KASHF)', click(1600), .9); add(kick(.7), 12.5, .5)
cue(12.6, 'riser', riser(.4), .6)
cue(13.0, 'whoosh (road into the phone)', whoosh(.5, 300, 6000), .8)
cue(13.35, 'ui click (screen opens)', click(), .8)
for t0 in (15.2, 16.8, 18.5, 20.2): cue(t0, 'swipe (screen push)', whoosh(.25, 1200, 7000), .5, .2); cue(t0, 'ui click', click(2200), .5)
cue(17.2, 'focus (interests)', click(1800), .6)
cue(19.7, 'tap', click(2600), .9)
cue(20.2, 'success chime', chime(note(84)), .7)
cue(20.9, 'whoosh (phone leaves)', whoosh(.4, 5000, 300), .6)
cue(21.0, 'whoosh (objects return)', whoosh(1.0, 200, 4000), .6)
cue(23.2, 'riser', riser(1.2), .7)
cue(24.5, 'bass hit (logo assembled)', impact(1.0), 1.0)
cue(26.0, 'whoosh (lockup)', whoosh(.5, 800, 6000), .6)
cue(26.3, 'shimmer (wordmark)', sparkle(.8), .8)
cue(27.2, 'soft hit (tagline)', impact(.35), 1.0); cue(27.2, 'chime', chime(note(88)), .6)
# fade-out last 1.2 s, soft limit
fo = np.ones(N); n = at(1.2); fo[-n:] = np.linspace(1, 0, n) ** 2
mix = np.stack([L, R], 1) * fo[:, None]
mix = np.tanh(mix / (np.abs(mix).max() * .9) * 1.2) * .7
out = os.environ.get('OUT', '.')
with wave.open(f'{out}/mix.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
json.dump(CUES, open(f'{out}/cues.json', 'w'), indent=0)
print('mix.wav', len(CUES), 'cues')
