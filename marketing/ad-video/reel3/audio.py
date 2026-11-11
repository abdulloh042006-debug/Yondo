"""Reel 3 soundtrack: original synthesis only (numpy), 48 kHz stereo, no samples, no voice.
Calm, cinematic, 80 BPM feel: void drone + sparse felt-piano (D major / B minor colour), sub swells on the big moments,
gentle pulse only under the app scene, warm open chord on the logo. Usage: OUT=<dir> python3 audio.py"""
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
def bell(m, dur=2.4, g=1.0): return tone(note(m), dur, 1.1, (1, .35, .12, .05)) * g
add(pad([note(38), note(45)], 10.5, 2.0, 500), 0.0, .55)                      # void drone D-A
add(pad([note(50), note(57), note(62), note(66)], 7.2, 1.5, 1200), 4.7, .32)  # the step opens the space (D maj)
for t0, m in [(1.0, 74), (2.5, 69), (4.75, 78), (6.1, 74), (6.55, 76), (7.0, 78), (7.45, 81), (8.6, 74)]: add(bell(m), t0, .26, (t0 % 1 - .5) * .6)
add(pad([note(47), note(54), note(59), note(62)], 3.2, 1.0, 1000), 10.0, .36)  # Bm: the question
add(pad([note(43), note(55), note(59), note(62)], 4.0, .6, 1600), 12.85, .4)  # G maj: YANGI TAJRIBA
for t0, m in [(10.3, 71), (11.0, 74), (11.6, 78), (12.85, 79), (13.3, 83), (15.5, 74), (16.2, 78)]: add(bell(m), t0, .24, (t0 % 1 - .5) * .6)
# app scene: soft pulse at 80 BPM (beat .75 s), D - A - Bm - G
B = .75; prog = [[38, 57, 62, 66], [45, 57, 61, 64], [47, 59, 62, 66], [43, 59, 62, 67]]
t = 17.0; i = 0
while t < 25.0 - 1e-6:
    ch = prog[i % 4]; dur = min(4 * B, 25.0 - t)
    add(pad([note(m) for m in ch[1:]], dur, .3, 1800), t, .3)
    for b in range(4):
        tb = t + b * B
        if tb >= 25: break
        add(kick(.5), tb, .32); add(tone(note(ch[0] + 12), .6, 3, (1, .5, .2)), tb, .2)
        add(tone(note(ch[1 + b % 3] + 12), .5, 4, (1, .3)), tb + B / 2, .1, (b % 2 - .5) * .6)
    t += 4 * B; i += 1
# ending: warm swell
add(pad([note(m) for m in [38, 50, 57, 62, 66, 69]], 6.2, 2.5, 2000), 25.0, .45)
for t0, m in [(25.6, 74), (26.6, 78), (27.6, 81), (28.6, 78), (29.6, 86)]: add(bell(m, 3.0), t0, .22, (t0 % 1 - .5) * .6)
add(pad([note(m) for m in [38, 45, 54, 57, 62, 69]], 3.2, .4, 2600), 31.0, .5)
add(tone(note(38), 3.0, .6, (1, .5, .25)), 31.0, .35)

# ---------- SFX (times = page.tpl.html cues) ----------
cue(0.0, 'ambient air (void)', lp(rng.standard_normal(at(4.0)), 900) * np.sin(np.linspace(0, np.pi, at(4.0))) * .25, 1.0)
cue(0.6, 'riser (camera closes in)', riser(3.0), .35)
cue(4.75, 'bass hit (first step)', impact(.8), 1.0)
for w in range(3): cue(4.75 + w * .35, 'light wave', whoosh(1.4, 3000, 300), .35)
for i in range(4): cue(6.1 + i * .45, 'place lights up', chime(note(81 + [0, 2, 4, 7][i])), .45, (i - 1.5) * .4)
cue(10.0, 'whoosh (formula in)', whoosh(1.0, 200, 3000), .5)
cue(11.3, 'shimmer (light between the ones)', sparkle(1.0), .7)
cue(12.6, 'riser', riser(.25), .5)
cue(12.85, 'bass hit (YANGI TAJRIBA)', impact(.8), 1.0)
for k in range(6): cue(14.8 + k * .27, 'footsteps', tick(), .25, (-1) ** k * .4)
cue(16.2, 'chime (wave hello)', chime(note(83)), .5)
cue(17.0, 'whoosh (light into the phone)', whoosh(1.0, 300, 4000), .6); cue(17.0, 'soft hit (light arrives)', impact(.45), 1.0)
cue(17.2, 'whoosh (camera orbit)', whoosh(1.6, 600, 2500), .22, -.3)
cue(18.0, 'ui click (screen on)', click(), 1.0); cue(18.0, 'soft hit (screen on)', impact(.4), 1.0)
for t0 in (20.3, 22.5, 23.9): cue(t0, 'ui click (screen change)', click(2200), .6)
cue(23.4, 'tap', click(2600), .8)
cue(23.9, 'success chime', chime(note(86)), .55)
cue(24.7, 'whoosh (bloom)', whoosh(.3, 4000, 300), .3)
cue(25.0, 'bass hit (ending)', impact(.85), 1.0); cue(25.0, 'click (cut)', click(900), .8)
for k in range(16): cue(25.4 + k * .36, 'footsteps', tick(), .18, (-1) ** k * .3)
cue(31.0, 'whoosh (point of light)', whoosh(.8, 300, 3000), .5)
cue(31.8, 'bass hit (logo node lands)', impact(.85), 1.0)
cue(32.1, 'shimmer (wordmark)', sparkle(.8), .7)
cue(32.5, 'soft hit (tagline)', impact(.3), 1.0)
# fade-out last 1.2 s, soft limit
fo = np.ones(N); n = at(1.2); fo[-n:] = np.linspace(1, 0, n) ** 2
mix = np.stack([L, R], 1) * fo[:, None]
mix = np.tanh(mix / (np.abs(mix).max() * .9) * 1.2) * .7
out = os.environ.get('OUT', '.')
with wave.open(f'{out}/mix.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
json.dump(CUES, open(f'{out}/cues.json', 'w'), indent=0)
print('mix.wav', len(CUES), 'cues')
