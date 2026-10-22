"""Original synthesized music bed + SFX + voices, per language. Output: out/mix-<lang>.wav (48 kHz stereo)."""
import json, sys, wave
import numpy as np

AD = '/tmp/claude-0/-home-claude/80ed5239-9a87-5b7a-bb32-cb2c8e001f18/scratchpad/ad'
SR = 48000
rng = np.random.default_rng(7)
TLS = json.load(open(f'{AD}/timeline.json'))


def tt(d):
    return np.arange(int(d * SR)) / SR


def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y


def lp_fft(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** 4), len(x))


def hp_fft(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR) + 1e-9
    return np.fft.irfft(X / np.sqrt(1 + (fc / f) ** 4), len(x))


def bp_sweep(noise, f0, f1, q=3.0, block=512):
    out = np.zeros_like(noise)
    n = len(noise)
    for s in range(0, n, block):
        k = s / max(1, n - 1)
        fc = f0 * (f1 / f0) ** k
        seg = noise[max(0, s - 2048):s + block]
        X = np.fft.rfft(seg); f = np.fft.rfftfreq(len(seg), 1 / SR)
        H = 1 / (1 + (q * (f / fc - fc / np.maximum(f, 1))) ** 2)
        y = np.fft.irfft(X * H, len(seg))
        out[s:s + block] = y[-min(block, n - s):]
    return out


def env_ad(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / max(a, 1e-4), 1) * np.exp(-np.maximum(t - a, 0) / d)


def nz(d):
    return rng.standard_normal(int(d * SR))


# ---------------- SFX ----------------
def s_riser(d):
    t = tt(d); n = len(t)
    x = bp_sweep(nz(d), 300, 6000, 2.0) * (t / d) ** 2 * 0.9
    x += 0.25 * np.sin(2 * np.pi * (110 * t + 400 * t ** 2 / d)) * (t / d) ** 2
    return x


def s_impact(big=False):
    d = 2.2 if big else 1.4
    t = tt(d)
    f = 34 + 110 * np.exp(-t * 18)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (2.2 if big else 3.5))
    crack = lp_fft(nz(d), 5000) * np.exp(-t * 28) * 0.6
    tail = lp_fft(nz(d), 1800) * np.exp(-t * 3.2) * (0.18 if big else 0.1)
    return (boom * 1.1 + crack + tail) * (1.0 if big else 0.8)


def s_whoosh(d=0.55, big=False):
    t = tt(d)
    x = bp_sweep(nz(d), 400 if not big else 250, 3500 if not big else 2500, 1.6)
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return x * e * (1.3 if big else 0.9)


def s_tap():
    t = tt(0.08)
    return (np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 90) * 0.5 + hp_fft(nz(0.08), 3000) * np.exp(-t * 160) * 0.35)


def s_tick():
    t = tt(0.05)
    return np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 140) * 0.35


def s_pop():
    t = tt(0.14)
    f = 520 + 700 * (1 - np.exp(-t * 40))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(len(t), 0.004, 0.045) * 0.55


def s_hit():
    t = tt(0.5)
    sn = bp_sweep(nz(0.5), 1800, 1200, 1.2) * np.exp(-t * 14) * 0.9
    sub = np.sin(2 * np.pi * (55 + 60 * np.exp(-t * 30)) * t) * np.exp(-t * 9) * 0.8
    return sn + sub


def bell(freqs, d, decay):
    t = tt(d); x = np.zeros(len(t))
    for i, (f, a) in enumerate(freqs):
        x += a * np.sin(2 * np.pi * f * t + i) * np.exp(-t * decay * (1 + 0.6 * i))
    return x * env_ad(len(t), 0.003, 10)


def s_ding():
    return bell([(1318.5, 0.5), (1975.5, 0.32), (2637, 0.12)], 1.4, 3.0) * 0.6


def s_chime():
    return bell([(659.3, 0.4), (987.8, 0.35), (1318.5, 0.25), (1975.5, 0.12)], 2.6, 1.6) * 0.65


SFX = {
    'riser': lambda e: s_riser(e[2]), 'impact': lambda e: s_impact(False), 'impact_big': lambda e: s_impact(True),
    'whoosh': lambda e: s_whoosh(0.55), 'whoosh_big': lambda e: s_whoosh(0.9, True), 'swipe': lambda e: s_whoosh(0.32) * 0.8,
    'tap': lambda e: s_tap(), 'tick': lambda e: s_tick(), 'pop': lambda e: s_pop(), 'hit': lambda e: s_hit(),
    'ding': lambda e: s_ding(), 'chime': lambda e: s_chime(), 'final': lambda e: s_impact(True) * 0.9 + np.pad(s_chime(), (0, int(2.2 * SR) - len(s_chime())))[:int(2.2 * SR)] if False else s_impact(True),
}
PAN = {'whoosh': 'sweep', 'whoosh_big': 'sweep', 'swipe': 'sweep'}


def place(buf, x, at, gain=1.0, pan=0.0, sweep=False):
    i = int(at * SR)
    if i >= buf.shape[1]:
        return
    x = x[:buf.shape[1] - i] * gain
    if sweep:
        p = np.linspace(-0.7, 0.7, len(x))
    else:
        p = np.full(len(x), pan)
    l = np.cos((p + 1) * np.pi / 4); r = np.sin((p + 1) * np.pi / 4)
    buf[0, i:i + len(x)] += x * l * 1.41
    buf[1, i:i + len(x)] += x * r * 1.41


# ---------------- music ----------------
def note(m):
    return 440 * 2 ** ((m - 69) / 12)


def saw(f, t):
    return 2 * ((f * t) % 1) - 1


def music(total, L, E, p7):
    n = int(total * SR); out = np.zeros((2, n))
    bpm = 120; beat = 60 / bpm; bar = 4 * beat
    down = L + 0.62                     # music "drops" on the logo impact
    prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [52, 55, 60]), (55, [55, 59, 62])]  # Am F C G
    # intro drone (ink section) and sad plucks (v2)
    t = tt(down)
    drone = (np.sin(2 * np.pi * note(33) * t) * 0.35 + np.sin(2 * np.pi * note(40) * t) * 0.18) * np.minimum(t / 0.8, 1)
    drone *= 0.5 + 0.5 * np.sin(2 * np.pi * 0.5 * t) ** 2
    place(out, drone * 0.55, 0)
    # heartbeat pulses during the hook
    for k in np.arange(1.0, TLS_cur['V'][1]['s'], 1.0):
        place(out, s_impact(False)[:int(0.5 * SR)] * 0.25, k)
    # pluck arpeggio in S2
    s2 = TLS_cur['V'][1]['s'] - 0.2
    arp = [69, 72, 76, 72, 69, 72, 76, 79]
    for i, m in enumerate(arp):
        at = s2 + i * beat / 2
        if at > down - 0.1:
            break
        tp = tt(1.2)
        pl = (np.sin(2 * np.pi * note(m) * tp) + 0.3 * np.sin(4 * np.pi * note(m) * tp)) * np.exp(-tp * 4)
        place(out, pl * 0.22, at, pan=0.3 * np.sin(i))
    # full section
    end_full = E + 0.2
    nbars = int(np.ceil((end_full - down) / bar)) + 1
    for b in range(nbars):
        bt = down + b * bar
        if bt >= end_full:
            break
        root, ch = prog[b % 4]
        d = min(bar, end_full - bt) + 0.6
        tp = tt(d)
        pad = sum(saw(note(m) * (1 + det), tp) for m in ch for det in (-0.004, 0.004)) / 6
        pad = lp_fft(pad, 1400) * np.minimum(tp / 0.25, 1) * np.exp(-np.maximum(tp - bar, 0) * 6)
        place(out, pad * 0.33, bt, pan=-0.2); place(out, pad * 0.33, bt + 0.012, pan=0.2)
        for k in range(8):                       # bass eighths
            at = bt + k * beat / 2
            if at >= end_full:
                break
            tb = tt(beat / 2)
            bs = np.sin(2 * np.pi * note(root - 24) * tb) + 0.4 * np.sign(np.sin(2 * np.pi * note(root - 24) * tb)) * 0.3
            place(out, bs * env_ad(len(tb), 0.005, 0.12) * 0.42, at)
        for k in range(4):
            at = bt + k * beat
            if at >= end_full:
                break
            tk = tt(0.35)
            kick = np.sin(2 * np.pi * np.cumsum(45 + 110 * np.exp(-tk * 35)) / SR) * np.exp(-tk * 9)
            place(out, kick * 0.85, at)
            if k in (1, 3):
                th = tt(0.25)
                clap = bp_sweep(nz(0.25), 1500, 1100, 1.0) * np.exp(-th * 22)
                place(out, clap * 0.35, at)
            th = tt(0.05)
            place(out, hp_fft(nz(0.05), 7000) * np.exp(-th * 90) * 0.22, at + beat / 2, pan=0.35)
    # end: sustained chord + low drone till the end
    te = tt(total - E)
    endpad = sum(saw(note(m) * (1 + det), te) for m in (57, 64, 69, 72) for det in (-0.003, 0.003)) / 8
    endpad = lp_fft(endpad, 900) * np.minimum(te / 1.2, 1) * np.clip((total - E - te) / 1.5, 0, 1)
    place(out, endpad * 0.32, E)
    return out


def load_voice(p):
    w = wave.open(p); sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
    t_old = np.arange(len(a)) / sr; t_new = np.arange(int(len(a) * SR / sr)) / SR
    return np.interp(t_new, t_old, a)


for lang in sys.argv[1:] or ['uz', 'ru']:
    TL = TLS[lang]; TLS_cur = TL
    total = TL['total']; n = int(total * SR)
    mus = music(total, TL['L'], TL['E'], TL['p7'])
    sfx = np.zeros((2, n))
    for e in TL['ev']:
        name = e[0]
        g = {'impact_big': 0.9, 'final': 1.0, 'riser': 0.55, 'tick': 0.6, 'tap': 0.7, 'pop': 0.6, 'hit': 0.6, 'ding': 0.55, 'chime': 0.6}.get(name, 0.7)
        place(sfx, SFX[name](e), e[1], gain=g, sweep=PAN.get(name) == 'sweep')
    # final chime with the "Tez kunda" hit
    place(sfx, s_chime() * 0.5, TL['p7'][2] + 0.05)
    vo = np.zeros(n); duck = np.ones(n)
    for i, v in enumerate(TL['V']):
        a = load_voice(f'{AD}/voice/{lang}-0{i + 1}.wav')
        s = int(v['s'] * SR); a = a[:n - s]; vo[s:s + len(a)] += a
        a0, a1 = max(0, s - int(0.12 * SR)), min(n, s + len(a) + int(0.15 * SR)); duck[a0:a1] = 0.42
    duck = np.convolve(duck, np.ones(int(0.08 * SR)) / int(0.08 * SR), 'same')
    # tiny room on sfx+music
    ir_t = tt(0.9); ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 6); ir /= np.abs(ir).sum() / 6
    def verb(x):
        return np.fft.irfft(np.fft.rfft(x, len(x) + len(ir)) * np.fft.rfft(ir, len(x) + len(ir)))[:len(x)]
    wet = np.stack([verb(mus[c] * 0.5 + sfx[c] * 0.5) for c in (0, 1)])
    mix = mus * duck * 0.5 + sfx * 0.75 + wet * 0.12
    mix += np.stack([vo, vo]) * 1.35
    mix /= max(1e-6, np.abs(mix).max()) / 0.89
    pcm = (np.clip(mix.T, -1, 1) * 32767).astype(np.int16)
    w = wave.open(f'{AD}/out/mix-{lang}.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close()
    print('mix', lang, round(total, 2), 's')
